"""
=================================================================
  SCRIPT TEST TOC DO PHAN HOI - SOCRATIC CHATBOT
  Do luong chi tiet tung giai doan: Network -> Backend -> AI
=================================================================

Các chỉ số được đo:
  - T_connect   : Thời gian thiết lập kết nối TCP (network handshake)
  - T_TTFB      : Time-To-First-Byte (backend nhận & bắt đầu xử lý)
  - T_orchestrator: Thời gian Orchestrator định tuyến (phân luồng AI)
  - T_first_token : Thời gian nhận token AI đầu tiên
  - T_stream    : Tổng thời gian nhận toàn bộ stream
  - T_total     : Tổng thời gian từ khi gửi đến khi nhận xong

Cách dùng:
  python scripts/speed_test.py
  python scripts/speed_test.py --url http://your-backend-url --runs 5
"""

import time
import json
import sys
import argparse
import statistics
from typing import Optional
import urllib.request
import urllib.error
import socket
import io

# Force stdout UTF-8 trên Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# -------------------------------------------------
#  CẤU HÌNH MẶC ĐỊNH
# -------------------------------------------------
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"
DEFAULT_SESSION_ID  = "guest-try-session"
DEFAULT_RUNS        = 3

TEST_PROMPTS = [
    "2 + 2 bang may?",
    "Tam giac co may goc?",
    "So nguyen to la gi?",
    "Cong thuc tinh dien tich hinh tron la gi?",
    "1 + 1 bang may thay?",
]

COLORS = {
    "reset":   "\033[0m",
    "bold":    "\033[1m",
    "red":     "\033[91m",
    "green":   "\033[92m",
    "yellow":  "\033[93m",
    "cyan":    "\033[96m",
    "magenta": "\033[95m",
    "blue":    "\033[94m",
    "white":   "\033[97m",
    "dim":     "\033[2m",
}

def c(color: str, text: str) -> str:
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"

def print_separator(char="-", width=70, color="dim"):
    print(c(color, char * width))

def print_header(title: str):
    print()
    print_separator("=", color="cyan")
    print(c("bold", f"  {title}"))
    print_separator("=", color="cyan")

def format_ms(ms: Optional[float]) -> str:
    if ms is None:
        return c("dim", "     N/A   ")
    if ms < 500:
        return c("green",  f"{ms:>8.1f} ms")
    elif ms < 2000:
        return c("yellow", f"{ms:>8.1f} ms")
    else:
        return c("red",    f"{ms:>8.1f} ms")

def check_backend_health(base_url: str) -> bool:
    try:
        req = urllib.request.Request(f"{base_url}/", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def measure_connection_time(host: str, port: int) -> Optional[float]:
    try:
        start = time.perf_counter()
        sock = socket.create_connection((host, port), timeout=10)
        elapsed = (time.perf_counter() - start) * 1000
        sock.close()
        return elapsed
    except Exception:
        return None

def run_single_test(base_url: str, session_id: str, prompt: str, run_idx: int) -> dict:
    """
    Thực hiện 1 lần test. Trả về dict kết quả với các chỉ số thời gian.
    """
    result = {
        "run": run_idx,
        "prompt": prompt,
        "T_total": None,
        "T_TTFB": None,
        "T_orchestrator": None,
        "T_first_token": None,
        "T_stream": None,
        "tokens_received": 0,
        "full_reply_length": 0,
        "target_agent": None,
        "error": None,
    }

    url = f"{base_url}/chat/orchestrator"
    payload = json.dumps({
        "session_id": session_id,
        "prompt": prompt,
        "problem_context": None,
    }).encode("utf-8")

    t_start = time.perf_counter()

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            # ── Đo TTFB ──────────────────────────────────────────
            t_ttfb = (time.perf_counter() - t_start) * 1000
            result["T_TTFB"] = t_ttfb

            t_stream_start = time.perf_counter()
            full_text = ""
            t_first_token = None
            token_count = 0
            current_event = None

            # Đọc từng DÒNG để đo timing chính xác từng SSE event
            # (tránh artifact khi đọc fixed-size chunk gộp nhiều events)
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                now_ms = (time.perf_counter() - t_start) * 1000

                if line.startswith("event:"):
                    current_event = line[6:].strip()

                elif line.startswith("data:"):
                    data_str = line[5:].strip()
                    if not data_str or data_str == "{}":
                        continue
                    try:
                        data_obj = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    if current_event == "orchestrator":
                        result["T_orchestrator"] = now_ms
                        result["target_agent"]   = data_obj.get("target_agent")

                    elif current_event == "message":
                        text_chunk = data_obj.get("text", "")
                        if text_chunk:
                            if t_first_token is None:
                                t_first_token = now_ms
                                result["T_first_token"] = t_first_token
                            full_text  += text_chunk
                            token_count += 1

                    elif current_event == "done":
                        break

            t_end = time.perf_counter()
            result["T_stream"]          = (t_end - t_stream_start) * 1000
            result["T_total"]           = (t_end - t_start) * 1000
            result["tokens_received"]   = token_count
            result["full_reply_length"] = len(full_text)

    except urllib.error.URLError as e:
        result["error"]   = f"URLError: {e.reason}"
        result["T_total"] = (time.perf_counter() - t_start) * 1000
    except Exception as e:
        result["error"]   = f"{type(e).__name__}: {e}"
        result["T_total"] = (time.perf_counter() - t_start) * 1000

    return result


def print_single_result(r: dict, run_num: int, total_runs: int):
    print()
    status = c("red", "X LOI") if r["error"] else c("green", "OK")
    print(f"  {c('bold', f'Run [{run_num}/{total_runs}]')}  prompt: {c('dim', repr(r['prompt'])[:50])}  [{status}]")
    print_separator()

    if r["error"]:
        print(f"  {c('red', 'Loi:')} {r['error']}")
        return

    rows = [
        ("TTFB (kết nối + server nhận)",  r["T_TTFB"],          "Từ khi gửi đến byte đầu tiên trả về"),
        ("Orchestrator routing",           r["T_orchestrator"],   "Backend phân tích & chọn agent AI"),
        ("Token AI đầu tiên",              r["T_first_token"],    "AI bắt đầu sinh câu trả lời"),
        ("Stream hoàn tất",                r["T_stream"],         "Nhận toàn bộ nội dung stream"),
        ("TONG THOI GIAN (E2E)",           r["T_total"],          "End-to-end: gửi → nhận xong"),
    ]

    for label, value, note in rows:
        print(f"  {label:<35} {format_ms(value)}   {c('dim', note)}")

    if r["target_agent"]:
        print(f"  {'Agent duoc chon':<35} {c('cyan', r['target_agent'])}")
    if r["full_reply_length"]:
        print(f"  {'Do dai phan hoi':<35} {c('dim', str(r['full_reply_length']) + ' ky tu')}")


def print_summary(results: list, conn_time: Optional[float]):
    print_header("TONG KET KET QUA TEST")

    ok_results = [r for r in results if not r["error"]]
    err_count  = len(results) - len(ok_results)

    print(f"\n  Tong so lan test : {c('bold', str(len(results)))}")
    print(f"  Thanh cong       : {c('green', str(len(ok_results)))}")
    if err_count:
        print(f"  Loi              : {c('red', str(err_count))}")
    if conn_time is not None:
        print(f"  Ket noi TCP      : {format_ms(conn_time)}")

    if not ok_results:
        print(c("red", "\n  Khong co ket qua hop le de thong ke!"))
        return

    metrics = [
        ("TTFB (Time-To-First-Byte)",   "T_TTFB"),
        ("Orchestrator routing",         "T_orchestrator"),
        ("Token AI dau tien",            "T_first_token"),
        ("Tong thoi gian (E2E)",         "T_total"),
    ]

    print()
    print(f"  {'Chi so':<32} {'Min':>10} {'Avg':>10} {'Max':>10} {'P50':>10}")
    print_separator()

    collected_avgs = {}

    for label, key in metrics:
        values = [r[key] for r in ok_results if r[key] is not None]
        if not values:
            print(f"  {label:<32} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>10}")
            continue

        values_sorted = sorted(values)
        avg = statistics.mean(values)
        p50 = statistics.median(values)
        collected_avgs[key] = avg

        def _fmt(v, _=None):
            if v < 500:   return c("green",  f"{v:>8.0f} ms")
            if v < 2000:  return c("yellow", f"{v:>8.0f} ms")
            return             c("red",    f"{v:>8.0f} ms")

        print(f"  {label:<32} {_fmt(min(values))} {_fmt(avg)} {_fmt(max(values))} {_fmt(p50)}")

    # Phân tích điểm nghẽn
    print()
    print_separator()
    print(c("bold", "  PHAN TICH DIEM NGHEN (Bottleneck Analysis):"))
    print()

    avg_ttfb  = collected_avgs.get("T_TTFB", 0)
    avg_orch  = collected_avgs.get("T_orchestrator", avg_ttfb)
    avg_first = collected_avgs.get("T_first_token", avg_orch)
    avg_total = collected_avgs.get("T_total", avg_first)

    net_overhead   = avg_ttfb
    orch_overhead  = max(avg_orch - avg_ttfb, 0)
    ai_first_token = max(avg_first - avg_orch, 0)
    ai_stream_rest = max(avg_total - avg_first, 0)
    total_measured = net_overhead + orch_overhead + ai_first_token + ai_stream_rest

    def pct(v):
        return (v / total_measured * 100) if total_measured > 0 else 0

    stages = [
        ("1. Network/Backend nhan req",  net_overhead),
        ("2. Orchestrator phan luong",   orch_overhead),
        ("3. AI sinh token dau tien",    ai_first_token),
        ("4. AI stream phan con lai",    ai_stream_rest),
    ]

    for stage, ms_val in stages:
        p = pct(ms_val)
        bar_len = int(p / 2.5)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        color = "green" if p < 20 else ("yellow" if p < 50 else "red")
        print(f"  {stage:<35} {format_ms(ms_val)} {c(color, bar)} {p:5.1f}%")

    # Kết luận tổng thể
    bottleneck = max(stages, key=lambda x: x[1])
    print()
    avg_e2e = avg_total
    if avg_e2e < 2000:
        verdict = c("green",  "OK - Tot (< 2s)")
    elif avg_e2e < 5000:
        verdict = c("yellow", "CHAP NHAN DUOC (2-5s)")
    else:
        verdict = c("red",    "CHAM - Can toi uu (> 5s)")

    print(f"  Toc do tong the   : {verdict}  (trung binh {avg_e2e:.0f}ms)")
    print(f"  Diem nghen chinh  : {c('bold', bottleneck[0])} ({bottleneck[1]:.0f}ms, {pct(bottleneck[1]):.1f}%)")

    # Gợi ý tối ưu
    print()
    print(c("bold", "  GOI Y TOI UU:"))
    suggestions = []
    if net_overhead > 300:
        suggestions.append("Network/TTFB cao → Kiem tra do tre mang, deploy backend gan hon")
    if orch_overhead > 1000:
        suggestions.append("Orchestrator cham → Toi uu DB query, them cache cho chat history")
    if ai_first_token > 3000:
        suggestions.append("AI phan hoi cham → Thu dung model nhe hon hoac giam max_output_tokens")
    if avg_e2e > 8000:
        suggestions.append("Tong thoi gian qua lon → Xem xet streaming UI hoac skeleton loading")

    if suggestions:
        for s in suggestions:
            print(c("yellow", f"  • {s}"))
    else:
        print(c("green", "  • He thong dang hoat dong on dinh! Khong co diem nghen nghiem trong."))

    print()
    print_separator("═", color="cyan")


# -------------------------------------------------
#  MAIN
# -------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Test toc do phan hoi Socratic Chatbot")
    parser.add_argument("--url",     default=DEFAULT_BACKEND_URL, help=f"Backend URL (default: {DEFAULT_BACKEND_URL})")
    parser.add_argument("--session", default=DEFAULT_SESSION_ID,  help=f"Session ID (default: {DEFAULT_SESSION_ID})")
    parser.add_argument("--runs",    default=DEFAULT_RUNS, type=int, help=f"So lan test (default: {DEFAULT_RUNS})")
    parser.add_argument("--prompt",  default=None, help="Custom prompt co dinh cho moi lan test")
    args = parser.parse_args()

    base_url   = args.url.rstrip("/")
    session_id = args.session
    num_runs   = args.runs

    # ── Hiển thị header ──
    print_header("SOCRATIC CHATBOT - SPEED TEST")
    print(f"\n  Backend URL : {c('cyan', base_url)}")
    print(f"  Session ID  : {c('cyan', session_id)}")
    print(f"  So lan test : {c('cyan', str(num_runs))}")
    print()

    # ── Kiểm tra backend ──
    print(f"  {c('dim', 'Kiem tra ket noi backend...')}", end=" ", flush=True)
    if not check_backend_health(base_url):
        print(c("red", "THAT BAI"))
        print(c("red", f"\n  Backend khong phan hoi tai: {base_url}"))
        print(c("dim",  "  Chay: uvicorn main:app --reload  (trong thu muc backend)"))
        sys.exit(1)
    print(c("green", "OK"))

    # ── Đo TCP latency ──
    from urllib.parse import urlparse
    parsed   = urlparse(base_url)
    host     = parsed.hostname or "127.0.0.1"
    port     = parsed.port or (443 if parsed.scheme == "https" else 80)
    conn_time = measure_connection_time(host, port)
    if conn_time is not None:
        print(f"  Do tre TCP  : {format_ms(conn_time)}")

    # ── Chạy test ──
    prompts = [args.prompt] * num_runs if args.prompt else \
              [TEST_PROMPTS[i % len(TEST_PROMPTS)] for i in range(num_runs)]

    print_header(f"DANG CHAY {num_runs} LAN TEST...")

    all_results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"\n  Lan {i}/{num_runs}...", end="", flush=True)
        result = run_single_test(base_url, session_id, prompt, i)
        all_results.append(result)
        print(c("green", " xong!"))
        print_single_result(result, i, num_runs)

        if i < num_runs:
            time.sleep(1.2)  # Tránh rate limit giữa các lần

    # ── Tổng kết ──
    print_summary(all_results, conn_time)


if __name__ == "__main__":
    main()
