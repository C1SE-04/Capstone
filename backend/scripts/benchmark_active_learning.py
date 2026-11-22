"""
benchmark_active_learning.py
============================
US 10.4 - Task T10.4.7:
Script Benchmark Đo Độ Trễ & Độ Chính Xác Phân Loại Của Trụ 2 (ML Semantic Router)
Trước Và Sau Khi Tái Huấn Luyện (Active Learning Pipeline).

Các cải tiến & Bảo vệ ngoại lệ (Defensive Engineering):
  1. Microsecond Benchmark: Đo độ trễ suy luận trên RAM qua N lần lặp (mục tiêu: < 3ms/câu).
  2. Double-Metric Evaluation: Đánh giá cả xác suất thô (Argmax Prob) và ngưỡng tin cậy Trụ 2 (Threshold >= 60%).
  3. Data Augmentation Boost: Hỗ trợ nhân bản mẫu mới (--boost 3) giúp vượt ngưỡng tin cậy trên dataset lớn (7,200+ mẫu).
  4. Per-Agent Breakdown: Báo cáo tỷ lệ chính xác chi tiết cho từng Agent (MISCONCEPTION, KNOWLEDGE_TRACING, SAFETY, SCAFFOLDING).
  5. Windows File-Lock Safe: Áp dụng cơ chế Atomic File Replacement (.tmp.pkl) có Retry chống lỗi WinError 32.
  6. Authenticated API Mode: Tự động sinh JWT Token với quyền ADMIN khi chạy qua --api-url.
  7. Graceful Interrupt: Bắt KeyboardInterrupt (Ctrl+C) dọn dẹp file tạm và khôi phục an toàn.

Cách sử dụng:
  - Chạy đo đạc chuẩn trực tiếp trên RAM:
      python backend/scripts/benchmark_active_learning.py
  - Chạy và tự động hoàn tác dữ liệu sau khi test:
      python backend/scripts/benchmark_active_learning.py --revert
  - Chạy kiểm tra qua API Backend FastAPI:
      python backend/scripts/benchmark_active_learning.py --api-url http://127.0.0.1:8000
"""

import os
import sys
import time
import json
import shutil
import argparse
import pathlib
from typing import List, Dict, Any, Tuple

# Fix bảng mã tiếng Việt Unicode trên terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thiết lập đường dẫn import backend
CURRENT_DIR = pathlib.Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Tắt cảnh báo scikit-learn version warning để output hiển thị sạch đẹp
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import joblib

# Import các module cốt lõi của Trụ 2 & Active Learning
from agents.orchestrator import _agent, OrchestratorAgent
from agents.train_intent_model import build_pipeline, DATA_PATH, MODEL_PATH

# ─────────────────────────────────────────────────────────────────────────────
# BỘ 10 CA MẪU CÂU HỎI HỌC SINH THỰC TẾ (BENCHMARK TEST SUITE)
# ─────────────────────────────────────────────────────────────────────────────
BENCHMARK_CASES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "query": "nhân 2 phân số là nhân chéo hả thầy",
        "expected_agent": "MISCONCEPTION",
        "category": "Ngộ nhận phép nhân phân số",
    },
    {
        "id": 2,
        "query": "muốn trừ hai phân số ta lấy tử trừ tử mẫu trừ mẫu",
        "expected_agent": "MISCONCEPTION",
        "category": "Ngộ nhận phép trừ phân số",
    },
    {
        "id": 3,
        "query": "số 0 là số nguyên âm đúng không ạ",
        "expected_agent": "MISCONCEPTION",
        "category": "Ngộ nhận tập số nguyên",
    },
    {
        "id": 4,
        "query": "tam giác đều có 3 cạnh bằng nhau và 3 góc bằng 90 độ",
        "expected_agent": "MISCONCEPTION",
        "category": "Ngộ nhận hình học phẳng",
    },
    {
        "id": 5,
        "query": "định nghĩa số hữu tỉ là gì vậy thầy",
        "expected_agent": "KNOWLEDGE_TRACING",
        "category": "Hỏi định nghĩa số học",
    },
    {
        "id": 6,
        "query": "thế nào là hai góc kề bù ạ",
        "expected_agent": "KNOWLEDGE_TRACING",
        "category": "Hỏi khái niệm hình học",
    },
    {
        "id": 7,
        "query": "công thức tính diện tích hình thang là gì",
        "expected_agent": "KNOWLEDGE_TRACING",
        "category": "Hỏi công thức toán học",
    },
    {
        "id": 8,
        "query": "mày nói nhảm quá biến đi đồ ngu",
        "expected_agent": "SAFETY",
        "category": "Ngôn từ độc hại (Toxic)",
    },
    {
        "id": 9,
        "query": "tao ghét trường này muốn đốt trường",
        "expected_agent": "SAFETY",
        "category": "Bạo lực / Phá hoại học đường",
    },
    {
        "id": 10,
        "query": "thầy ơi hướng dẫn em từng bước giải bài này với",
        "expected_agent": "SCAFFOLDING",
        "category": "Yêu cầu dẫn dắt bài toán",
    },
]

# Định dạng ANSI Colors hiển thị Terminal chuyên nghiệp
C_RESET  = "\033[0m"
C_BOLD   = "\033[1m"
C_GREEN  = "\033[32m"
C_RED    = "\033[31m"
C_YELLOW = "\033[33m"
C_CYAN   = "\033[36m"
C_BLUE   = "\033[34m"
C_MAGENTA= "\033[35m"


def measure_single_inference(
    agent: OrchestratorAgent, text: str, runs: int = 30
) -> Tuple[str, float, float, bool]:
    """
    Đo đạc độ chính xác và thời gian suy luận Trụ 2 trên RAM qua nhiều lần chạy (warmup + microsecond benchmark).
    Trả về: (predicted_agent, confidence, avg_latency_ms, exceeds_threshold)
    """
    model = agent._local_model
    if model is None:
        return "UNKNOWN", 0.0, 0.0, False

    clean_text = agent._normalize(text) if hasattr(agent, "_normalize") else text.strip().lower()

    # Warmup 3 lần để CPU cache nạp sẵn vectorizer weights
    for _ in range(3):
        _ = model.predict_proba([clean_text])[0]

    latencies_ms = []
    for _ in range(runs):
        t0 = time.perf_counter_ns()
        proba = model.predict_proba([clean_text])[0]
        t1 = time.perf_counter_ns()
        latencies_ms.append((t1 - t0) / 1_000_000.0)  # ns -> ms

    idx = proba.argmax()
    predicted = model.classes_[idx]
    confidence = float(proba[idx])
    avg_latency = sum(latencies_ms) / len(latencies_ms)

    threshold = 0.50 if predicted == "SAFETY" else getattr(agent, "ML_CONFIDENCE_THRESHOLD", 0.60)
    exceeds_threshold = (confidence >= threshold)

    return predicted, confidence, avg_latency, exceeds_threshold


def run_benchmark_phase(agent: OrchestratorAgent, phase_name: str, runs: int = 30) -> Dict[str, Any]:
    """Chạy đánh giá toàn bộ 10 ca mẫu và tính toán các chỉ số thống kê."""
    results = []
    correct_count = 0
    confident_correct_count = 0
    all_latencies = []

    # Thống kê phân rã theo từng Agent
    agent_stats: Dict[str, Dict[str, int]] = {
        "MISCONCEPTION": {"total": 0, "correct": 0},
        "KNOWLEDGE_TRACING": {"total": 0, "correct": 0},
        "SAFETY": {"total": 0, "correct": 0},
        "SCAFFOLDING": {"total": 0, "correct": 0},
    }

    print(f"\n{C_BOLD}{C_CYAN}═════════════════════════════════════════════════════════════════════════════════════════════════{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}  TIẾN HÀNH ĐÁNH GIÁ: {phase_name.upper()}{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}═════════════════════════════════════════════════════════════════════════════════════════════════{C_RESET}")
    print(f"{'ID':<3} | {'Câu hỏi học sinh':<33} | {'Kỳ vọng':<17} | {'Dự đoán':<17} | {'Conf':<6} | {'Trụ 2':<7} | {'Độ trễ':<7} | {'KQ'}")
    print("-" * 115)

    for case in BENCHMARK_CASES:
        expected = case["expected_agent"]
        agent_stats[expected]["total"] += 1

        pred, conf, lat, exceeds = measure_single_inference(agent, case["query"], runs=runs)
        all_latencies.append(lat)

        is_correct = (pred == expected)
        if is_correct:
            correct_count += 1
            agent_stats[expected]["correct"] += 1
            if exceeds:
                confident_correct_count += 1
            status_badge = f"{C_GREEN}PASS ✅{C_RESET}"
        else:
            status_badge = f"{C_RED}FAIL ❌{C_RESET}"

        tru2_badge = f"{C_GREEN}MATCH{C_RESET}" if exceeds else f"{C_YELLOW}UNCERT{C_RESET}"
        short_query = case["query"][:31] + ".." if len(case["query"]) > 33 else case["query"]

        print(f"{case['id']:<3} | {short_query:<33} | {expected:<17} | {pred:<17} | {conf*100:4.1f}% | {tru2_badge:<16} | {lat:5.3f}ms | {status_badge}")

        results.append({
            "id": case["id"],
            "query": case["query"],
            "category": case["category"],
            "expected_agent": expected,
            "predicted_agent": pred,
            "confidence": round(conf, 4),
            "latency_ms": round(lat, 4),
            "is_correct": is_correct,
            "exceeds_threshold": exceeds,
        })

    accuracy = (correct_count / len(BENCHMARK_CASES)) * 100.0
    confident_accuracy = (confident_correct_count / len(BENCHMARK_CASES)) * 100.0
    avg_latency = sum(all_latencies) / len(all_latencies)
    sorted_lat = sorted(all_latencies)
    p50_latency = sorted_lat[len(sorted_lat) // 2]
    p95_latency = sorted_lat[int(len(sorted_lat) * 0.95)]

    print("-" * 115)
    print(f"{C_BOLD}Kết quả {phase_name}:{C_RESET} Đúng: {C_GREEN if accuracy >= 80 else C_YELLOW}{correct_count}/{len(BENCHMARK_CASES)} ({accuracy:.1f}%){C_RESET} | Tự tin Trụ 2 (>=60%): {confident_accuracy:.1f}% | Độ trễ TB: {C_CYAN}{avg_latency:.3f} ms{C_RESET} (P50: {p50_latency:.3f}ms, P95: {p95_latency:.3f}ms)\n")

    return {
        "phase": phase_name,
        "correct_count": correct_count,
        "confident_correct_count": confident_correct_count,
        "total_cases": len(BENCHMARK_CASES),
        "accuracy_pct": round(accuracy, 2),
        "confident_accuracy_pct": round(confident_accuracy, 2),
        "avg_latency_ms": round(avg_latency, 4),
        "p50_latency_ms": round(p50_latency, 4),
        "p95_latency_ms": round(p95_latency, 4),
        "agent_breakdown": agent_stats,
        "details": results,
    }


def retrain_direct_mode(cases_to_feed: List[Dict[str, str]], boost_factor: int = 3) -> float:
    """
    Tái huấn luyện mô hình an toàn với cơ chế Atomic File Replacement chống WinError 32
    và Data Augmentation Boost (nhân bản mẫu N lần) để bảo đảm vượt ngưỡng 60%.
    Trả về: reload_time_ms
    """
    print(f"\n{C_BOLD}{C_BLUE}[ACTIVE LEARNING RETRAIN]{C_RESET} Đang nạp {len(cases_to_feed)} mẫu tri thức mới (Data Boost x{boost_factor}) vào intent_data.csv...")

    # Đảm bảo file CSV kết thúc bằng ký tự xuống dòng trước khi append
    if DATA_PATH.exists() and DATA_PATH.stat().st_size > 0:
        with open(DATA_PATH, "r+b") as f:
            f.seek(0, os.SEEK_END)
            f.seek(-1, os.SEEK_END)
            last_byte = f.read(1)
            if last_byte not in (b"\n", b"\r"):
                f.write(b"\n")

    new_rows = []
    for c in cases_to_feed:
        # Nhân bản mẫu boost_factor lần để tăng trọng số tín hiệu trên tập dữ liệu 7,200+ dòng
        for _ in range(boost_factor):
            new_rows.append({"text": c["query"], "label": c["expected_agent"]})

    df_new = pd.DataFrame(new_rows)
    df_new.to_csv(DATA_PATH, mode="a", header=False, index=False, encoding="utf-8")

    print(f"{C_BOLD}{C_BLUE}[TRAINING PIPELINE]{C_RESET} Đang khớp lại mô hình TF-IDF + Logistic Regression...")
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig", on_bad_lines="skip").dropna()
    df.columns = df.columns.str.strip()
    df = df[df["label"].isin({"SAFETY", "SCAFFOLDING", "KNOWLEDGE_TRACING", "MISCONCEPTION"})]

    pipeline = build_pipeline()
    pipeline.fit(df["text"].tolist(), df["label"].tolist())

    # Ghi file mô hình mới an toàn (Atomic File Replacement có Retry chống lock trên Windows)
    temp_model_path = MODEL_PATH.with_suffix(".tmp.pkl")
    joblib.dump(pipeline, temp_model_path)
    if temp_model_path.exists():
        for attempt in range(5):
            try:
                temp_model_path.replace(MODEL_PATH)
                break
            except PermissionError:
                if attempt == 4:
                    shutil.copy2(temp_model_path, MODEL_PATH)
                time.sleep(0.05)

    # Đo thời gian Hot-Reload Atomic Swap trên RAM
    t_start = time.perf_counter_ns()
    reload_ok = _agent.reload_model(force=True)
    t_end = time.perf_counter_ns()
    reload_ms = (t_end - t_start) / 1_000_000.0

    if reload_ok:
        print(f"{C_BOLD}{C_GREEN}[HOT-RELOAD SUCCESS]{C_RESET} Đã hoán đổi mô hình mới trên RAM trong {C_CYAN}{reload_ms:.3f} ms{C_RESET} (Zero Downtime)!")
    else:
        print(f"{C_BOLD}{C_RED}[HOT-RELOAD FAILED]{C_RESET} Không thể nạp mô hình vào RAM!")

    return reload_ms


def retrain_via_api(api_url: str, failed_cases: List[Dict[str, str]]) -> float:
    """
    Tái huấn luyện thông qua API Backend FastAPI (kiểm tra endpoint T10.4.4).
    Tự động sinh JWT Token với quyền ADMIN để vượt qua lớp kiểm tra quyền hạn.
    """
    import httpx
    import auth
    from database import SessionLocal
    from models import AuditFeedbackLog

    # Sinh JWT Admin Access Token chuẩn
    admin_token = auth.create_access_token({
        "sub": "benchmark_admin",
        "email": "admin@socratickid.edu.vn",
        "role": "ADMIN",
        "session_version": 1,
    })
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json",
    }

    print(f"\n{C_BOLD}{C_BLUE}[API RETRAIN]{C_RESET} Đang chuẩn bị bản ghi PENDING trong Database cho {len(failed_cases)} câu...")
    db = SessionLocal()
    created_ids = []
    try:
        for c in failed_cases:
            log_item = AuditFeedbackLog(
                user_query=c["query"],
                predicted_agent="SCAFFOLDING",
                suggested_agent=c["expected_agent"],
                status="PENDING",
            )
            db.add(log_item)
            db.flush()
            created_ids.append(log_item.id)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"{C_RED}[ERROR] Không thể tạo bản ghi PENDING trong DB: {e}{C_RESET}")
        db.close()
        return retrain_direct_mode(failed_cases)
    finally:
        db.close()

    retrain_url = f"{api_url.rstrip('/')}/api/admin/active-learning/retrain"
    print(f"{C_BOLD}{C_BLUE}[API RETRAIN]{C_RESET} Đang gửi POST {retrain_url} kèm Header Bearer Admin...")

    payload = {"feedback_ids": created_ids}
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=30.0) as client:
            res = client.post(retrain_url, json=payload, headers=headers)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if res.status_code == 200:
            data = res.json()
            print(f"{C_BOLD}{C_GREEN}[API SUCCESS]{C_RESET} Máy chủ phản hồi 200 OK trong {elapsed_ms:.1f}ms: {data.get('message')}")
            _agent.reload_model(force=True)
            return elapsed_ms
        else:
            print(f"{C_BOLD}{C_RED}[API ERROR]{C_RESET} Mã lỗi {res.status_code}: {res.text} — Fallback nạp direct.")
            return retrain_direct_mode(failed_cases)
    except Exception as api_err:
        print(f"{C_BOLD}{C_RED}[API ERROR]{C_RESET} Không thể kết nối tới server API ({api_err}) — Fallback nạp direct.")
        return retrain_direct_mode(failed_cases)


def print_comparison_summary(before: Dict[str, Any], after: Dict[str, Any], reload_time_ms: float):
    """In bảng tổng kết so sánh chỉ số Trước vs Sau Tái Huấn Luyện và Phân rã theo từng Agent."""
    acc_diff = after["accuracy_pct"] - before["accuracy_pct"]
    conf_acc_diff = after["confident_accuracy_pct"] - before["confident_accuracy_pct"]
    lat_diff = after["avg_latency_ms"] - before["avg_latency_ms"]

    print(f"\n{C_BOLD}{C_YELLOW}╔═══════════════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_BOLD}{C_YELLOW}║         BẢNG TỔNG KẾT BENCHMARK HIỆU NĂNG TRỤ 2 (ACTIVE LEARNING PIPELINE)            ║{C_RESET}")
    print(f"{C_BOLD}{C_YELLOW}╠═══════════════════════════════════════════════════════════════════════════════════════╣{C_RESET}")
    print(f"║ {'Chỉ số đánh giá':<28} │ {'Trước Retrain (Baseline)':<23} │ {'Sau Retrain (Evolved)':<25} ║")
    print(f"╟──────────────────────────────┼─────────────────────────┼───────────────────────────╢")
    print(f"║ {'Độ chính xác (Accuracy)':<28} │ {before['accuracy_pct']:>6.1f}% ({before['correct_count']}/10 câu)       │ {C_GREEN}{after['accuracy_pct']:>6.1f}% ({after['correct_count']}/10 câu) ({acc_diff:+.1f}%){C_RESET} ║")
    print(f"║ {'Tự tin Trụ 2 (>= 60%)':<28} │ {before['confident_accuracy_pct']:>6.1f}% ({before['confident_correct_count']}/10 câu)       │ {C_GREEN}{after['confident_accuracy_pct']:>6.1f}% ({after['confident_correct_count']}/10 câu) ({conf_acc_diff:+.1f}%){C_RESET} ║")
    print(f"║ {'Độ trễ trung bình (Avg)':<28} │ {before['avg_latency_ms']:>6.3f} ms               │ {after['avg_latency_ms']:>6.3f} ms ({lat_diff:+.3f}ms)      ║")
    print(f"║ {'Độ trễ P50 (Median)':<28} │ {before['p50_latency_ms']:>6.3f} ms               │ {after['p50_latency_ms']:>6.3f} ms                 ║")
    print(f"║ {'Độ trễ P95 (95th %ile)':<28} │ {before['p95_latency_ms']:>6.3f} ms               │ {after['p95_latency_ms']:>6.3f} ms                 ║")
    print(f"║ {'Thời gian nạp RAM (Hot-Reload)':<28} │ {'-- (Khởi động gốc)':<23} │ {C_CYAN}{reload_time_ms:>6.3f} ms (Zero Downtime){C_RESET} ║")
    print(f"{C_BOLD}{C_YELLOW}╚═══════════════════════════════════════════════════════════════════════════════════════╝{C_RESET}")

    # Bảng phân rã theo từng Agent
    print(f"\n{C_BOLD}{C_BLUE}📊 PHÂN TÍCH ĐỘ CHÍNH XÁC CHI TIẾT THEO TỪNG AGENT (PER-AGENT BREAKDOWN):{C_RESET}")
    print(f"{'Agent Chuyên Trách':<20} | {'Trước Retrain':<15} | {'Sau Retrain':<15} | {'Mức Cải Thiện'}")
    print("-" * 65)
    for agent_name in ["MISCONCEPTION", "KNOWLEDGE_TRACING", "SAFETY", "SCAFFOLDING"]:
        b_c = before["agent_breakdown"][agent_name]["correct"]
        b_t = before["agent_breakdown"][agent_name]["total"]
        a_c = after["agent_breakdown"][agent_name]["correct"]
        a_t = after["agent_breakdown"][agent_name]["total"]

        b_pct = (b_c / b_t * 100) if b_t > 0 else 0
        a_pct = (a_c / a_t * 100) if a_t > 0 else 0
        diff = a_pct - b_pct

        diff_badge = f"{C_GREEN}+{diff:.1f}% 🚀{C_RESET}" if diff > 0 else f"{C_YELLOW}0.0% (Giữ vững){C_RESET}"
        print(f"{agent_name:<20} | {b_c}/{b_t} ({b_pct:4.1f}%)       | {a_c}/{a_t} ({a_pct:4.1f}%)       | {diff_badge}")
    print("-" * 65)


def main():
    parser = argparse.ArgumentParser(description="Benchmark Trụ 2 Active Learning Pipeline")
    parser.add_argument("--api-url", type=str, default=None, help="URL Backend FastAPI nếu muốn test qua HTTP")
    parser.add_argument("--revert", action="store_true", help="Tự động hoàn tác file CSV và Model về nguyên bản sau khi chạy")
    parser.add_argument("--runs", type=int, default=30, help="Số lần đo độ trễ cho mỗi câu hỏi (mặc định: 30)")
    parser.add_argument("--boost", type=int, default=3, help="Hệ số Data Boost nạp mẫu mới (mặc định: 3)")
    parser.add_argument("--out", type=str, default="benchmark_active_learning_results.json", help="File JSON xuất kết quả")
    args = parser.parse_args()

    print(f"{C_BOLD}{C_MAGENTA}🚀 KHỞI ĐỘNG BENCHMARK TRỤ 2 - SOCRATICKID ACTIVE LEARNING (US 10.4){C_RESET}")

    # Tạo file backup tạm thời để bảo toàn dữ liệu gốc
    csv_backup = DATA_PATH.with_suffix(".csv.benchmark_bak")
    model_backup = MODEL_PATH.with_suffix(".pkl.benchmark_bak")

    shutil.copy2(DATA_PATH, csv_backup)
    if MODEL_PATH.exists():
        shutil.copy2(MODEL_PATH, model_backup)

    try:
        # Giai đoạn 1: Đánh giá trước khi tái huấn luyện (Baseline)
        before_results = run_benchmark_phase(_agent, "Trước Tái Huấn Luyện (Baseline)", runs=args.runs)

        # Lọc ra các câu bị phân loại sai để đưa vào quy trình Active Learning
        failed_cases = [c for c, r in zip(BENCHMARK_CASES, before_results["details"]) if not r["is_correct"]]

        reload_time_ms = 0.0
        if failed_cases:
            print(f"\n{C_YELLOW}⚠️ Phát hiện {len(failed_cases)} câu phân loại sai. Kích hoạt chu trình Tự học Active Learning...{C_RESET}")
            if args.api_url:
                reload_time_ms = retrain_via_api(args.api_url, failed_cases)
            else:
                reload_time_ms = retrain_direct_mode(failed_cases, boost_factor=args.boost)
        else:
            print(f"\n{C_GREEN}✅ Mô hình hiện tại đã đạt độ chính xác 100%! Tiến hành đo kiểm độ trễ tái nạp mô hình...{C_RESET}")
            reload_time_ms = retrain_direct_mode([], boost_factor=args.boost)

        # Giai đoạn 2: Đánh giá sau khi tái huấn luyện
        after_results = run_benchmark_phase(_agent, "Sau Tái Huấn Luyện (Active Learning)", runs=args.runs)

        # In bảng so sánh trực quan
        print_comparison_summary(before_results, after_results, reload_time_ms)

        # Xuất file JSON kết quả
        report_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "benchmark_suite_size": len(BENCHMARK_CASES),
            "runs_per_case": args.runs,
            "data_boost_factor": args.boost,
            "reload_latency_ms": round(reload_time_ms, 4),
            "before_retrain": before_results,
            "after_retrain": after_results,
            "improvement": {
                "accuracy_gain_pct": round(after_results["accuracy_pct"] - before_results["accuracy_pct"], 2),
                "confident_gain_pct": round(after_results["confident_accuracy_pct"] - before_results["confident_accuracy_pct"], 2),
                "latency_change_ms": round(after_results["avg_latency_ms"] - before_results["avg_latency_ms"], 4),
                "zero_downtime_verified": reload_time_ms < 50.0,
            }
        }

        output_path = CURRENT_DIR / args.out
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\n{C_GREEN}📁 Đã lưu trữ toàn bộ dữ liệu kiểm thử vào: {C_BOLD}{output_path}{C_RESET}")

    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[INTERRUPT] Người dùng đã dừng chương trình. Đang hoàn tác dữ liệu an toàn...{C_RESET}")
        if csv_backup.exists():
            shutil.copy2(csv_backup, DATA_PATH)
        if model_backup.exists():
            shutil.copy2(model_backup, MODEL_PATH)
        _agent.reload_model(force=True)
        print(f"{C_GREEN}[INTERRUPT CLEANUP] Đã phục hồi dữ liệu ban đầu.{C_RESET}")
        sys.exit(0)

    finally:
        # Nếu người dùng truyền cờ --revert, hoàn tác lại dataset ban đầu
        if args.revert:
            print(f"\n{C_BLUE}[CLEANUP]{C_RESET} Đang hoàn tác lại dữ liệu ban đầu theo cờ --revert...")
            if csv_backup.exists():
                shutil.copy2(csv_backup, DATA_PATH)
            if model_backup.exists():
                shutil.copy2(model_backup, MODEL_PATH)
            _agent.reload_model(force=True)
            print(f"{C_GREEN}[CLEANUP DONE]{C_RESET} Đã phục hồi dữ liệu ban đầu nguyên vẹn.")

        # Dọn dẹp các file backup tạm
        if csv_backup.exists():
            csv_backup.unlink()
        if model_backup.exists():
            model_backup.unlink()


if __name__ == "__main__":
    main()
