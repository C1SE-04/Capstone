"""
test_emotion_flag.py
====================
Chay: cd D:\Document\Capstone\backend && python scripts/test_emotion_flag.py

Kiem tra xem ham _determine_emotion_flag (va toan bo pipeline route_sync)
tra dung co cam xuc chua.

Cot ket qua:
  [PASS] ✅  -> Dung nhu mong doi
  [FAIL] ❌  -> Sai -- in them agent, flag thuc te, scratchpad de debug
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import OrchestratorAgent

# Khoi tao agent (load ML model)
_agent = OrchestratorAgent()

TEST_CASES = [

    # NHOM 1: CORRECT - Hoc sinh tra loi dung (co problem_context)
    ("C1. Dung - so nguyen",           "x = 2",              {"correctSolution": "2"},    "CORRECT"),
    ("C2. Dung - kem loi giai",        "em tinh duoc x = 2", {"correctSolution": "2"},    "CORRECT"),
    ("C3. Dung - so thuc",             "x = 0.5",            {"correctSolution": "0.5"},  "CORRECT"),
    ("C4. Dung - so am",               "x = -3",             {"correctSolution": "-3"},   "CORRECT"),
    ("C5. Dung - phan so",             "ket qua la 1/2",     {"correctSolution": "1/2"},  "CORRECT"),

    # NHOM 2: WRONG - Sai so (co problem_context)
    ("W1. Sai - so khac",              "x = 5",              {"correctSolution": "2"},    "WRONG"),
    ("W2. Sai - gan dung",             "x = 3",              {"correctSolution": "2"},    "WRONG"),
    ("W3. Sai - dau am",               "x = -2",             {"correctSolution": "2"},    "WRONG"),
    ("W4. Sai - so lon",               "x = 999",            {"correctSolution": "2"},    "WRONG"),

    # NHOM 3: WRONG - Tu nhan hieu sai (KHONG co problem_context) -- hay bi bug
    ("W5. Tu nhan - tuong",            "em tưởng đây là đáp án đúng nhưng thầy bảo sai", None, "WRONG"),
    ("W6. Tu nhan - nham",             "em bị nhầm rồi thầy ơi",                          None, "WRONG"),
    ("W7. Tu nhan - lon",              "em lộn chiều bất đẳng thức",                      None, "WRONG"),
    ("W8. Tu nhan - sai roi",          "sai rồi em hiểu ra rồi",                          None, "WRONG"),
    ("W9. Tu nhan - hieu sai",         "em hiểu sai khái niệm từ đầu",                    None, "WRONG"),
    ("W10. Tu nhan - nghi sai",        "em nghĩ sai bước này",                            None, "WRONG"),
    ("W11. Tu nhan - toan hoc",        "em tưởng âm nhân âm ra âm",                         None, "WRONG"),

    # NHOM 4: GUIDING - Hoi ly thuyet / xin goi y
    ("G1. Hoi ly thuyet",              "phan so la gi thay",       None, "GUIDING"),
    ("G2. Xin goi y",                  "bi qua thay oi cho hint",  None, "GUIDING"),
    ("G3. Khong biet lam",             "thay oi em khong biet lam", None, "GUIDING"),
    ("G4. Chao hoi",                   "chao thay",                None, "GUIDING"),
    ("G5. Tra loi cut",                "da",                       None, "GUIDING"),
    ("G6. Cau chung chung",            "ok thay",                  None, "GUIDING"),
    ("G7. Hoi ve loi sai (k tu nhan)", "thay oi loi sai la gi",   None, "GUIDING"),
    ("G8. Xin goi y bai toan",         "em khong hieu thay goi y cho em voi", None, "GUIDING"),

    # NHOM 5: WARNING - Ngon ngu xuc pham
    ("X1. Chui the nhe",               "dm thay",   None, "WARNING"),
    ("X2. Xuc pham",                   "thay ngu vl", None, "WARNING"),
]

GROUPS = {
    "NHOM 1 - CORRECT (co problem_context)":          [c for c in TEST_CASES if c[0].startswith("C")],
    "NHOM 2 - WRONG (sai so, co problem_context)":    [c for c in TEST_CASES if c[0].startswith("W") and int(c[0][1]) <= 4],
    "NHOM 3 - WRONG (tu nhan, KHONG co ctx) [DE BUG]":[c for c in TEST_CASES if c[0].startswith("W") and int(c[0][1]) >= 5],
    "NHOM 4 - GUIDING (hoi, goi y, chao)":            [c for c in TEST_CASES if c[0].startswith("G")],
    "NHOM 5 - WARNING (xuc pham)":                    [c for c in TEST_CASES if c[0].startswith("X")],
}

EMOJI = {"CORRECT": "✅ CORRECT", "WRONG": "❌ WRONG", "GUIDING": "💡 GUIDING", "WARNING": "⚠️  WARNING"}

def run_tests():
    total_pass = total_fail = 0
    failed_cases = []

    print("=" * 70)
    print("  TEST CO CAM XUC CON CU (emotion_flag) - ORCHESTRATOR")
    print("=" * 70)

    for group_name, cases in GROUPS.items():
        print(f"\n--- {group_name} ---")
        for desc, msg, ctx, expected in cases:
            result = _agent.route_sync(
                latest_message=msg,
                history_text="",
                problem_context=ctx,
            )
            actual  = result.get("emotion_flag", "MISSING")
            agent   = result.get("selected_agent", "?")
            scratch = result.get("routing_scratchpad", "")
            ok      = (actual == expected)

            if ok:
                total_pass += 1
                print(f"  PASS  {desc}")
                print(f"        agent={agent}  flag={EMOJI.get(actual, actual)}")
            else:
                total_fail += 1
                failed_cases.append((desc, msg, ctx, expected, actual, agent, scratch))
                print(f"  FAIL  {desc}")
                print(f"        Mong doi : {EMOJI.get(expected, expected)}")
                print(f"        Thuc te  : {EMOJI.get(actual, actual)}   (agent={agent})")
                print(f"        Tin nhan : \"{msg}\"")
                print(f"        Scratchpad: {scratch!r}")

    total = total_pass + total_fail
    print(f"\n{'=' * 70}")
    print(f"  KET QUA: {total_pass}/{total} PASS  |  {total_fail} FAIL")
    print(f"{'=' * 70}")

    if total_fail == 0:
        print("  Tat ca PASS! Con cu dang nhan dung co cam xuc.")
    else:
        print(f"  Con {total_fail} case bi sai!\n")
        print("  Danh sach FAIL:")
        for i, (desc, msg, ctx, expected, actual, agent, scratch) in enumerate(failed_cases, 1):
            print(f"  {i}. [{desc}]")
            print(f"     msg    = \"{msg}\"")
            print(f"     ctx    = {ctx}")
            print(f"     expect = {expected}  got = {actual}  (agent={agent})")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    run_tests()
