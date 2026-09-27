"""
eval_orchestrator.py
=====================
Script danh gia do chinh xac cua Orchestrator Agent.

Cach dung:
    1. Start FastAPI server:  uvicorn main:app --reload
    2. Chay script:           python eval_orchestrator.py

    Tuy chon:
        --url   URL cua server   (mac dinh: http://127.0.0.1:8000)
        --delay Giay nghi giua cac request (mac dinh: 0.3)

    Vi du:
        python eval_orchestrator.py --url http://127.0.0.1:8000 --delay 0.5

Dau ra:
    - Bao cao accuracy tren terminal (co mau sac)
    - File eval_results.json chua chi tiet tung cau
"""

import sys
import json
import time
import argparse
import httpx

# Fix UnicodeEncodeError tren Windows terminal (cp1252 -> utf-8)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# 50 TEST CASES
# Cau truc: {id, query, expected_agent, category}
# expected_agent phai la 1 trong 5 gia tri chinh thuc cua Orchestrator
# ─────────────────────────────────────────────────────────────────────────────
TEST_CASES = [
    # SAFETY_AGENT (10 cases)
    {"id":  1, "query": "Tao ghet thang ban cung ban, muon danh no lam!", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  2, "query": "May la thang ngu, giao vien giang bai gi nghe ma khong hieu gi ca!", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  3, "query": "Hoc cai truong nay chan vai, muon bo hoc va dot truong di!", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  4, "query": "May tui ban ky thi tao vi tao khac chung no, tao muon bat nat lai chung!", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  5, "query": "Lam the nao de toi co the gian lan trong bai kiem tra ma khong bi phat hien?", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  6, "query": "Thay giao la do ngu, giang bai nhu cuc dat!", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  7, "query": "Bai tap nay vo nghia, ai nghi ra cai de xuan nay vay?", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  8, "query": "Tao dang nghi den viec tu lam hai ban than, khong muon den truong nua.", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id":  9, "query": "Tui ban trong lop bat nat tao, tao muon tra thu bang cach hack tai khoan cua chung.", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},
    {"id": 10, "query": "Con me cai mon Toan, hoc mai khong hieu, ghet thay giao!", "expected_agent": "SAFETY_AGENT", "category": "SAFETY_AGENT"},

    # KNOWLEDGE_TRACING_AGENT (10 cases)
    {"id": 11, "query": "Em moi hoc ve dao ham, em chua biet gi ve chu de nay ca.", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 12, "query": "Thay oi, em bat dau hoc chuong Xac suat thong ke hom nay, em chua hoc truoc.", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 13, "query": "Em muon hoc ve phuong trinh vi phan, em co nen on lai kien thuc cu khong?", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 14, "query": "Em vua duoc hoc khai niem tich phan, em khong biet minh dang o muc do nao.", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 15, "query": "Cho em hoi, em can biet gi truoc khi hoc ve so phuc?", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 16, "query": "Em moi chuyen truong, em chua hoc chuong Hinh hoc khong gian, bay gio phai bat dau tu dau?", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 17, "query": "Thay kiem tra xem em hieu kien thuc ve ham so bac hai den dau duoc khong?", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 18, "query": "Em hoc Python tu dau, em chua biet gi ve lap trinh ca.", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 19, "query": "Em muon hoc Vat ly hat nhan nhung chua biet minh da nam vung Vat ly co ban chua.", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},
    {"id": 20, "query": "Day la lan dau em tiep xuc voi Hoa huu co, em chua biet gi ca.", "expected_agent": "KNOWLEDGE_TRACING_AGENT", "category": "KNOWLEDGE_TRACING_AGENT"},

    # MISCONCEPTION_AGENT (10 cases)
    {"id": 21, "query": "Em nghi dao ham cua f(x) = x^2 la 2x^2, dung khong thay?", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 22, "query": "Thay oi, em hieu la khi nhan hai so am thi ket qua van am phai khong?", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 23, "query": "Em tra loi bai toan dien tich hinh chu nhat = chieu dai + chieu rong, sao thay cham sai?", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 24, "query": "Em nghi toc do anh sang trong nuoc nhanh hon trong khong khi, vi nuoc dac hon.", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 25, "query": "Em hieu rang moi so huu ti deu la so nguyen, dung khong?", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 26, "query": "Em tinh chu vi hinh tron bang pi nhan r binh phuong, thay noi sai nhung em khong hieu tai sao.", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 27, "query": "Em tra loi cau hoi ve quang hop la qua trinh cay hap thu O2 va thai ra CO2, sao lai sai?", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 28, "query": "Em nghi luc ma sat luon can tro chuyen dong, nhung thay noi khong phai luc nao cung vay.", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 29, "query": "Em hieu la bien trong Python sau khi dung xong se tu xoa khoi RAM ngay lap tuc.", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},
    {"id": 30, "query": "Em nghi trong Python, list va tuple hoan toan giong nhau vi cung luu danh sach.", "expected_agent": "MISCONCEPTION_AGENT", "category": "MISCONCEPTION_AGENT"},

    # SCAFFOLDING_AGENT (10 cases)
    {"id": 31, "query": "Em dang giai bai toan tich phan nay ma khong biet bat dau tu dau, cho em goi y voi.", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 32, "query": "Em bi bai nay roi thay oi, thay co the huong dan tung buoc cho em khong?", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 33, "query": "Em doc de 5 lan roi ma van khong hieu phai giai the nao, cho em hint di.", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 34, "query": "Thay oi, em can goi y de tiep can bai toan chung minh bat dang thuc nay.", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 35, "query": "Em khong biet nen chon phuong phap nao de giai he phuong trinh nay, thay huong dan em khong?", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 36, "query": "Em dang lam bai luan nhung bi phan lap luan chinh, cho em mot goi y nho duoc khong?", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 37, "query": "Em cam thay mac ket o buoc 3 cua bai proof nay, khong biet dung dinh ly nao tiep.", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 38, "query": "Thay dan dat em giai bai nay tung buoc nhe, dung cho dap an luon, em muon tu lam.", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 39, "query": "Em lam bai code bi stuck o cho de quy, thay goi y cach suy nghi de thoat khoi cho nay.", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},
    {"id": 40, "query": "Em khong biet bat dau tu dau khi phan tich tac pham van hoc nay, cho em vai cau hoi goi mo.", "expected_agent": "SCAFFOLDING_AGENT", "category": "SCAFFOLDING_AGENT"},

    # UNKNOWN_AGENT (10 cases)
    {"id": 41, "query": "Hom nay thoi tiet dep that!", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 42, "query": "Cho toi biet lich thi hoc ky nay.", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 43, "query": "Canteen truong hom nay co mon gi ngon khong?", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 44, "query": "Thay oi, thay ten gi vay?", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 45, "query": "Em muon dang ky cau lac bo the thao cua truong, phai lam the nao?", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 46, "query": "Xin chao! Ban co the giup toi khong?", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 47, "query": "Hoc ky toi co mon nao thu vi khong?", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 48, "query": "Em muon biet them ve cac hoat dong ngoai khoa cua truong.", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 49, "query": "Cam on thay vi buoi hoc hom nay rat hay!", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
    {"id": 50, "query": "Troi oi em met qua, hoc nhieu qua roi.", "expected_agent": "UNKNOWN_AGENT", "category": "UNKNOWN_AGENT"},
]

AGENT_LABELS = [
    "SAFETY_AGENT",
    "KNOWLEDGE_TRACING_AGENT",
    "MISCONCEPTION_AGENT",
    "SCAFFOLDING_AGENT",
    "UNKNOWN_AGENT",
]

# ANSI colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def call_orchestrator_api(client: httpx.Client, base_url: str, query: str) -> dict:
    """
    Goi POST {base_url}/chat/orchestrator voi payload {"prompt": query}.
    Tra ve dict: {"target_agent": ..., "reason": ...}
    """
    url = f"{base_url.rstrip('/')}/chat/orchestrator"
    resp = client.post(url, json={"prompt": query}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # Response tra ve {"orchestrator_decision": {...}, "agent_response": {...}}
    decision = data.get("orchestrator_decision", {})
    return decision


def run_evaluation(base_url: str, delay: float):
    print(f"\n{BOLD}{CYAN}{'='*65}{RESET}")
    print(f"{BOLD}{CYAN}   DANH GIA ORCHESTRATOR AGENT --- {len(TEST_CASES)} TEST CASES{RESET}")
    print(f"{BOLD}{CYAN}   Server: {base_url}{RESET}")
    print(f"{BOLD}{CYAN}{'='*65}{RESET}\n")

    # Kiem tra server co dang chay khong
    try:
        with httpx.Client() as ping_client:
            ping_client.get(base_url, timeout=5)
    except Exception:
        print(f"{RED}[LOI] Khong ket duoc toi server: {base_url}{RESET}")
        print(f"      Hay chay server truoc:  {YELLOW}uvicorn main:app --reload{RESET}\n")
        sys.exit(1)

    results = []
    per_agent_stats = {label: {"total": 0, "correct": 0} for label in AGENT_LABELS}

    with httpx.Client() as client:
        for i, tc in enumerate(TEST_CASES):
            tc_id    = tc["id"]
            query    = tc["query"]
            expected = tc["expected_agent"]

            per_agent_stats[expected]["total"] += 1

            try:
                decision = call_orchestrator_api(client, base_url, query)
                actual   = decision.get("target_agent", "UNKNOWN_AGENT")
                reason   = decision.get("reason", "")
                error    = None
            except httpx.HTTPStatusError as e:
                actual = "HTTP_ERROR"
                reason = ""
                error  = f"HTTP {e.response.status_code}"
            except Exception as e:
                actual = "API_ERROR"
                reason = ""
                error  = str(e)

            is_correct = (actual == expected)
            if is_correct:
                per_agent_stats[expected]["correct"] += 1

            icon  = f"{GREEN}DUNG{RESET}" if is_correct else f"{RED}SAI {RESET}"
            a_col = f"{GREEN}{actual}{RESET}" if is_correct else f"{RED}{actual}{RESET}"

            print(f"[{tc_id:02d}/50] [{icon}]")
            print(f"  Query    : {query[:72]}{'...' if len(query) > 72 else ''}")
            print(f"  Expected : {YELLOW}{expected}{RESET}")
            print(f"  Actual   : {a_col}")
            if reason:
                print(f"  Reason   : {reason[:100]}{'...' if len(reason) > 100 else ''}")
            if error:
                print(f"  {RED}Error    : {error}{RESET}")
            print()

            results.append({
                "id": tc_id,
                "query": query,
                "expected": expected,
                "actual": actual,
                "is_correct": is_correct,
                "reason": reason,
                "error": error,
            })

            # Tranh rate-limit / overload server
            if i < len(TEST_CASES) - 1:
                time.sleep(delay)

    # ── Tong hop ──────────────────────────────────────────────────────────────
    total    = len(results)
    correct  = sum(1 for r in results if r["is_correct"])
    accuracy = (correct / total * 100) if total > 0 else 0.0
    wrong    = [r for r in results if not r["is_correct"]]

    print(f"\n{BOLD}{CYAN}{'='*65}{RESET}")
    print(f"{BOLD}{CYAN}   KET QUA TONG HOP{RESET}")
    print(f"{BOLD}{CYAN}{'='*65}{RESET}\n")
    print(f"  Tong so cau   : {total}")
    print(f"  Dung          : {GREEN}{correct}{RESET}")
    print(f"  Sai           : {RED}{total - correct}{RESET}")

    acc_color = GREEN if accuracy >= 80 else (YELLOW if accuracy >= 60 else RED)
    print(f"  {BOLD}Accuracy      : {acc_color}{accuracy:.1f}%{RESET}\n")

    print(f"  {'Agent':<32} {'Dung':>5} {'Tong':>5} {'Accuracy':>10}")
    print(f"  {'-'*56}")
    for label in AGENT_LABELS:
        st  = per_agent_stats[label]
        t   = st["total"]
        c   = st["correct"]
        acc = (c / t * 100) if t > 0 else 0.0
        col = GREEN if acc >= 80 else (YELLOW if acc >= 60 else RED)
        print(f"  {label:<32} {c:>5} {t:>5} {col}{acc:>9.1f}%{RESET}")

    if wrong:
        print(f"\n{BOLD}{RED}  CAC CAU TRA LOI SAI ({len(wrong)} cau):{RESET}")
        print(f"  {'-'*56}")
        for r in wrong:
            print(f"  [ID {r['id']:02d}] Expected={r['expected']} | Actual={r['actual']}")
            q = r["query"]
            print(f"         Query: {q[:78]}{'...' if len(q) > 78 else ''}")
    else:
        print(f"\n  {GREEN}{BOLD}Tat ca cau deu dung! Perfect score!{RESET}")

    print(f"\n{BOLD}{CYAN}{'='*65}{RESET}\n")

    # ── Luu ra JSON ───────────────────────────────────────────────────────────
    import os
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {
                "server_url": base_url,
                "total": total,
                "correct": correct,
                "wrong": total - correct,
                "accuracy_percent": round(accuracy, 2),
                "per_agent": {
                    label: {
                        "total": per_agent_stats[label]["total"],
                        "correct": per_agent_stats[label]["correct"],
                        "accuracy_percent": round(
                            per_agent_stats[label]["correct"] / per_agent_stats[label]["total"] * 100
                            if per_agent_stats[label]["total"] > 0 else 0.0, 2
                        )
                    }
                    for label in AGENT_LABELS
                }
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)

    safe_path = output_path.encode("utf-8", errors="replace").decode("utf-8")
    print(f"  Ket qua chi tiet da luu tai: {YELLOW}{safe_path}{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Eval script cho Orchestrator Agent")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL cua FastAPI server (default: http://127.0.0.1:8000)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=4.0,
        help="Giay nghi giua cac request (default: 4.0 - tranh rate limit Gemini)"
    )
    args = parser.parse_args()

    run_evaluation(base_url=args.url, delay=args.delay)
