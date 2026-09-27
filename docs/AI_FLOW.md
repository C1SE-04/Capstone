### 1. Luồng của MISCONCEPTION AGENT (Phát hiện & Nắn chỉnh hiểu sai)

> 📌 **Tình huống:** Khi học sinh đưa ra một đáp án sai kinh điển: **`"Em tính ra bằng 5/7 ạ!"`**  
> *(Học sinh ngộ nhận cộng tử với tử $2+3=5$, mẫu với mẫu $3+4=7$).*

```
[Học sinh gửi: "Em tính ra bằng 5/7 ạ!"]
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 1. LẦN GỌI GEMINI THỨ NHẤT: Bác Lễ tân (Orchestrator)                 │
│    - Nháp trong routing_scratchpad:                                    │
│      "Bài toán 2/3 + 3/4 = 17/12. Học sinh lấy (2+3)/(3+4) = 5/7.      │
│       Đây là lỗi sai ngộ nhận: cộng tử với tử, mẫu với mẫu!"          │
│    - Ra quyết định: Bàn giao cho Bác Sĩ Bắt Lỗi (MISCONCEPTION)        │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Trả JSON về cho Backend Python)
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. LẦN GỌI GEMINI THỨ HAI: Bác Sĩ Bắt Lỗi (Misconception Agent)        │
│    - Nhận task: Chỉ ra bước sai mà KHÔNG ĐƯỢC nói đáp án đúng là 17/12.│
│    - Nháp trong internal_scratchpad:                                   │
│      "Học sinh sai ở chỗ cộng 2 mẫu số 3 + 4 = 7.                      │
│       Cần hỏi lại để học sinh tự nhận ra quy tắc cộng phân số."       │
│    - Soạn bản nháp (draft_response):                                   │
│      "Thầy thấy em lấy 2+3=5 và 3+4=7 đúng không? Nhưng với hai        │
│       phân số khác mẫu, chúng mình có được cộng thẳng hai mẫu số       │
│       với nhau như vậy không nhỉ?"                                     │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Trả bản nháp về cho Backend Python)
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. LẦN GỌI GEMINI THỨ BA: Giám khảo Sư phạm (Reviewer)                │
│    - Kiểm tra checklist vi phạm:                                       │
│      ✓ Có nói đáp án 17/12 không? -> KHÔNG.                            │
│      ✓ Có làm tính hộ không? -> KHÔNG.                                 │
│      ✓ Có hỏi đúng chỗ sai để học sinh tự nhận thức? -> CÓ.            │
│    - Chấm điểm: confidence_score = 0.95 -> PASS!                       │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Duyệt xong)
                    ▼
 [Frontend: Cú Socratic đổi vẻ mặt 'Ồ, chưa đúng rồi' (wrong_first_attempt)
  và hiện câu hỏi nắn chỉnh của Gia sư lên khung chat]
```

---

### 2. Luồng của KNOWLEDGE TRACING AGENT (Dò tìm lỗ hổng kiến thức nền)

> 📌 **Tình huống:** Học sinh hoàn toàn bế tắc hoặc nói: **`"Thầy ơi em quên sạch cách làm rồi, không biết bắt đầu từ đâu cả."`**  
> *(Hệ thống cần kiểm tra xem học sinh có còn nhớ khái niệm BCNN hay cách tìm mẫu số chung của lớp 4 không).*

```
[Học sinh gửi: "Em quên sạch cách làm rồi thầy ơi..."]
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 1. LẦN GỌI GEMINI THỨ NHẤT: Bác Lễ tân (Orchestrator)                 │
│    - Nháp trong routing_scratchpad:                                    │
│      "Học sinh bị hổng kiến thức nền, không biết bắt đầu từ đâu.       │
│       Cần đo lường xem học sinh hiểu tới đâu về mẫu số chung."        │
│    - Ra quyết định: Bàn giao cho Thầy Đo Kiến Thức (KNOWLEDGE_TRACING) │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Trả JSON về cho Backend Python)
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. LẦN GỌI GEMINI THỨ HAI: Thầy Đo Kiến Thức (Knowledge Tracing Agent) │
│    - Nhận task: Đặt 1 câu hỏi kiểm tra khái niệm nền tảng cốt lõi.     │
│    - Nháp trong internal_scratchpad:                                   │
│      "Bài toán cần mẫu chung của 3 và 4. Ta sẽ lùi lại 1 bước:         │
│       hỏi xem học sinh có tìm được số nào cùng chia hết cho 3 và 4."   │
│    - Soạn bản nháp (draft_response):                                   │
│      "Đừng lo lắng em nhé! Thầy trò mình cùng đi từ bước đơn giản      │
│       nhất nào. Em có tìm được một số nào (khác 0) mà vừa chia hết     │
│       cho 3, lại vừa chia hết cho 4 không?"                            │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Trả bản nháp về cho Backend Python)
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. LẦN GỌI GEMINI THỨ BA: Giám khảo Sư phạm (Reviewer)                │
│    - Kiểm tra checklist vi phạm:                                       │
│      ✓ Có lộ kết quả 17/12 không? -> KHÔNG.                            │
│      ✓ Có hỏi dồn dập nhiều câu không? -> KHÔNG (chỉ 1 câu nền tảng).  │
│      ✓ Tông giọng có động viên, thân thiện không? -> CÓ.               │
│    - Chấm điểm: confidence_score = 0.95 -> PASS!                       │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Duyệt xong)
                    ▼
 [Frontend: Cú Socratic chuyển sang trạng thái ân cần, lắng nghe (chat)
  và gửi câu hỏi gợi nhớ kiến thức lớp 4 cho học sinh]
```

---

### 3. Luồng của SAFETY AGENT (Xử lý ngoài lề & Giữ an toàn)

> 📌 **Tình huống:** Học sinh hỏi câu ngoài bài học: **`"Thầy ơi thầy có chơi Roblox không, vào solo với em ván đi!"`**  
> *(Học sinh mất tập trung, hỏi chuyện chơi game ngoài phạm vi học tập).*

```
[Học sinh gửi: "Thầy ơi thầy có chơi Roblox không, vào solo với em đi!"]
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 1. LẦN GỌI GEMINI THỨ NHẤT: Bác Lễ tân (Orchestrator)                 │
│    - Nháp trong routing_scratchpad:                                    │
│      "Tin nhắn học sinh rủ chơi game Roblox, không liên quan bài toán   │
│       phân số. Cần từ chối nhẹ nhàng và đưa học sinh về bài học."      │
│    - Ra quyết định: Bàn giao cho Vệ Sĩ An Toàn (SAFETY)                │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Trả JSON về cho Backend Python)
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. LẦN GỌI GEMINI THỨ HAI: Vệ Sĩ An Toàn (Safety Agent)                │
│    - Nhận task: Từ chối vui vẻ, không chỉ trích, kéo về bài toán 2/3 + 3/4│
│    - Nháp trong internal_scratchpad:                                   │
│      "Không mắng học sinh. Trả lời hóm hỉnh rồi hỏi lại bài toán."     │
│    - Soạn bản nháp (draft_response):                                   │
│      "Haha, thầy chỉ mê môn Toán thôi nè! 😉 Chúng mình cùng giải      │
│       quyết xong bài cộng phân số 2/3 + 3/4 này đã nhé! Em đã quan sát  │
│       thấy mẫu số của hai bạn ấy có gì đặc biệt chưa?"                 │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Trả bản nháp về cho Backend Python)
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. LẦN GỌI GEMINI THỨ BA: Giám khảo Sư phạm (Reviewer)                │
│    - Kiểm tra checklist vi phạm:                                       │
│      ✓ Có phán xét, mắng mỏ học sinh không? -> KHÔNG.                  │
│      ✓ Có kéo học sinh về lại bài học một cách tự nhiên không? -> CÓ.  │
│    - Chấm điểm: confidence_score = 1.0 -> PASS!                        │
└───────────────────┬────────────────────────────────────────────────────┘
                    │ (Duyệt xong)
                    ▼
 [Frontend: Cú Socratic chuyển sang trạng thái nhắc nhở vui vẻ (off_topic)
  và hiển thị câu từ chối hóm hỉnh kèm câu hỏi kéo về bài học]
```
### 4. Luồng của Scaffolding AGENT (Xử lý tính toán)
[Học sinh gửi: "2/3 + 3/4 = mấy"]
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│ 1. LẦN GỌI GEMINI THỨ NHẤT: Bác Lễ tân (Orchestrator)  │
│    - Đọc câu hỏi, tự nhẩm: "À, bài phân số mới toanh"  │
│    - Ra quyết định: Bàn giao task cho Thầy Gợi Mở!     │
└────────────────────────┬───────────────────────────────┘
                         │ (Trả JSON về cho Backend Python)
                         ▼
┌────────────────────────────────────────────────────────┐
│ 2. LẦN GỌI GEMINI THỨ HAI: Thầy Gợi Mở (Scaffolding)   │
│    - Nhận task từ Backend                              │
│    - Tự nháp chi tiết: 8/12 + 9/12 = 17/12             │
│    - Giấu đáp án 17/12, soạn câu gợi mở:               │
│      "Em thấy mẫu số 3 và 4 thế nào với nhau?"         │
└────────────────────────┬───────────────────────────────┘
                         │ (Trả bản nháp về cho Backend Python)
                         ▼
┌────────────────────────────────────────────────────────┐
│ 3. LẦN GỌI GEMINI THỨ BA: Giám khảo (Reviewer)         │
│    - Độc lập chấm điểm câu của Thầy Gợi Mở             │
│    - "Có lộ số 17/12 không? Không. Đạt chuẩn, PASS!"   │
└────────────────────────┬───────────────────────────────┘
                         │ (Duyệt xong)
                         ▼
             [Gửi đến màn hình học sinh]
Dưới đây là sơ đồ luồng chi tiết của **3 Agent còn lại** (Misconception, Knowledge Tracing, Safety) theo đúng quy chuẩn 3 lần gọi Gemini của hệ thống:

---
