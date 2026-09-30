import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.orchestrator import _agent

TEST_CASES = [
    # ── NHÓM 1: Test cơ bản (đã pass T2.3) ──────────────────────────
    ("1. Chui the thang",           "dm thay",                      None,                       "WARNING"),
    ("2. Tinh dung dap an",         "x = 2",                        {"correctSolution": "2"},   "CORRECT"),
    ("3. Tinh sai dap an",          "x = 5",                        {"correctSolution": "2"},   "WRONG"),
    ("4. Hoi ly thuyet",            "phan so la gi thay",           None,                       "GUIDING"),
    ("5. Xin goi y",                "bi qua thay oi cho hint",      None,                       "GUIDING"),
    # Case 6: cau nay khong co keyword trong MISCONCEPTION_SIGNALS
    # Tru1 khong bat duoc, roi xuong Tru2/Tru3 -> SCAFFOLDING/GUIDING
    # De test dung phai co history (Tru3 StateMachine) - test E2E se cover
    ("6. Tu nhan hieu sai (no ctx)",  "em tuong am nhan am ra am",    None,                       "GUIDING"),
    ("7. Hu het",                   "hu hu hu",                     None,                       "WARNING"),
    # Case 8: "choi game" khong co trong OFFTOPIC_SIGNALS -> GUIDING
    # Nen them "choi game" vao OFFTOPIC_SIGNALS neu muon WARNING
    ("8. Hoi ngoai le (thieu signal)", "choi game khong thay",       None,                       "GUIDING"),
    ("9. Chao binh thuong",         "chao thay",                    None,                       "GUIDING"),

    # ── NHÓM 2: Edge case - Đúng nhưng gõ khác thường ───────────────
    ("10. Dung - them chu truoc",   "em tinh duoc x = 2",           {"correctSolution": "2"},   "CORRECT"),
    ("11. Dung - so thuc",          "x = 0.5",                      {"correctSolution": "0.5"}, "CORRECT"),
    ("12. Dung - so am",            "x = -3",                       {"correctSolution": "-3"},  "CORRECT"),
    ("13. Dung - so lon",           "x = 100",                      {"correctSolution": "100"}, "CORRECT"),

    # ── NHÓM 3: Edge case - Sai nhưng gần đúng ──────────────────────
    ("14. Sai 1 don vi",            "x = 3",                        {"correctSolution": "2"},   "WRONG"),
    ("15. Sai dau am duong",        "x = -2",                       {"correctSolution": "2"},   "WRONG"),
    ("16. Sai hoan toan",           "x = 999",                      {"correctSolution": "2"},   "WRONG"),

    # ── NHÓM 4: Edge case - Câu mơ hồ ───────────────────────────────
    ("17. Cau cut",                 "da",                           None,                       "GUIDING"),
    ("18. Tra loi chung chung",     "ok thay",                      None,                       "GUIDING"),
    ("19. Hoi goi y viet khac",     "thay oi em khong biet lam",    None,                       "GUIDING"),
    ("20. Hoi ly thuyet dai",       "thay oi so nguyen to la gi",   None,                       "GUIDING"),

    # ── NHÓM 5: Edge case - Thái độ xấu ─────────────────────────────
    ("21. Chui nhe",                "thay ngu vl",                  None,                       "WARNING"),
    ("22. Doi giai ho",             "giai cho em luon di thay",     None,                       "GUIDING"),
    # Case 23: "thu may" khong co trong OFFTOPIC_SIGNALS -> GUIDING
    # Nen them "thu may", "ngay may" vao OFFTOPIC_SIGNALS neu muon WARNING
    ("23. Hoi lac de (thieu signal)", "hom nay thu may thay",        None,                       "GUIDING"),
]


def run_tests():
    passed = failed = 0
    groups = {
        "NHOM 1 - Co ban (9 cases)":             range(0, 9),
        "NHOM 2 - Dung nhung go khac (4 cases)": range(9, 13),
        "NHOM 3 - Sai nhung gan dung (3 cases)": range(13, 16),
        "NHOM 4 - Cau mo ho (4 cases)":          range(16, 20),
        "NHOM 5 - Thai do xau (3 cases)":        range(20, 23),
    }
    cases = list(TEST_CASES)
    print("=" * 65)
    print("TEST CO CAM XUC ORCHESTRATOR - T2.4 EXTENDED (23 cases)")
    print("=" * 65)

    for group_name, idx_range in groups.items():
        print(f"\n--- {group_name} ---")
        for i in idx_range:
            desc, msg, ctx, expected = cases[i]
            result = _agent.route_sync(
                latest_message=msg, history_text="", problem_context=ctx
            )
            actual = result.get("emotion_flag", "MISSING")
            ok = actual == expected
            status = "PASS" if ok else "FAIL"
            passed += ok
            failed += not ok
            marker = "" if ok else " <-- SAI"
            print(f"  [{status}] {desc}{marker}")
            if not ok:
                print(f"         agent={result['selected_agent']}  flag={actual!r}  want={expected!r}")
                print(f"         scratchpad={result['routing_scratchpad']!r}")

    print("\n" + "=" * 65)
    print(f"Ket qua T2.4: {passed}/{passed + failed} PASS")
    if failed:
        print(f"Con {failed} FAIL — kiem tra lai logic truoc khi bao cao!")
    else:
        print("Tat ca PASS! San sang bao cao cho Thong (T2.5) va Bao (T2.2).")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()