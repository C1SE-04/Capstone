import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.orchestrator import _agent

TEST_CASES = [
    # (mô_tả, tin_nhắn, problem_context, emotion_flag_kỳ_vọng)
    ("Học sinh chửi thề",          "đm thầy",                    None,                     "WARNING"),
    ("Học sinh tính đúng",         "x = 2",                      {"correctSolution": "2"}, "CORRECT"),
    ("Học sinh tính sai",          "x = 5",                      {"correctSolution": "2"}, "WRONG"),
    ("Học sinh hỏi lý thuyết",     "phân số là gì thầy",         None,                     "GUIDING"),
    ("Học sinh xin gợi ý",         "bí quá thầy ơi cho hint",    None,                     "GUIDING"),
    ("Học sinh hiểu sai",          "em tưởng âm nhân âm ra âm",  None,                     "WRONG"),
    ("Học sinh hú hét",            "hú hú hú",                   None,                     "WARNING"),
    ("Học sinh hỏi ngoài lề",      "chơi game không thầy",       None,                     "WARNING"),
    ("Học sinh chào bình thường",  "chào thầy",                  None,                     "GUIDING"),
]

def run_tests():
    passed = failed = 0
    print("=" * 60)
    print("TEST CO CAM XUC ORCHESTRATOR")
    print("=" * 60)
    for desc, msg, ctx, expected in TEST_CASES:
        result = _agent.route_sync(
            latest_message=msg, history_text="", problem_context=ctx
        )
        actual = result.get("emotion_flag", "MISSING")
        ok = actual == expected
        status = "PASS" if ok else "FAIL"
        passed += ok
        failed += not ok
        print(f"[{status}] {desc}")
        print(f"  msg={msg!r}  agent={result['selected_agent']}  flag={actual!r}  want={expected!r}")
    print("=" * 60)
    print(f"Ket qua: {passed}/{passed+failed} PASS")
    if failed:
        print(f"Con {failed} FAIL — kiem tra lai logic emotion_flag!")

if __name__ == "__main__":
    run_tests()