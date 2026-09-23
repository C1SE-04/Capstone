import sys
sys.stdout.reconfigure(encoding='utf-8')

from agents.orchestrator import _agent

print("--- BẮT ĐẦU TEST TRỤ 1 ---")

# Test 1: Từ cấm → SAFETY
r = _agent.route_sync('sao bài khó thế ê')
print('Test 1:', r['selected_agent'], '|', r['routing_scratchpad'])

# Test 2: Hỏi lý thuyết → KNOWLEDGE_TRACING
r = _agent.route_sync('liệu định nghĩa của đạo hàm có liên quan gì đến tích phân')
print('Test 2:', r['selected_agent'], '|', r['routing_scratchpad'])

# Test 3: Nộp đáp án đúng → SCAFFOLDING
r = _agent.route_sync('dạ bằng 11/24', problem_context={'correctSolution': '11/24'})
print('Test 3:', r['selected_agent'], '|', r['routing_scratchpad'])

# Test 4: Nộp đáp án sai → MISCONCEPTION
r = _agent.route_sync('mẫu số luôn lớn hơn tử số', problem_context={'correctSolution': 'tử số có thể lớn hơn mẫu số'})
print('Test 4:', r['selected_agent'], '|', r['routing_scratchpad'])

# Test 5: Cầu cứu → SCAFFOLDING
r = _agent.route_sync('bí rồi thầy ơi giúp em với')
print('Test 5:', r['selected_agent'], '|', r['routing_scratchpad'])

# Test 6: Câu chào → SAFETY
r = _agent.route_sync('chào thầy ạ')
print('Test 6:', r['selected_agent'], '|', r['routing_scratchpad'])

print("--- KẾT THÚC TEST ---")
