import sys
import pathlib
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report
import joblib

HERE        = pathlib.Path(__file__).parent
DATA_PATH   = HERE / "intent_data.csv"
MODEL_PATH  = HERE / "local_orchestrator.pkl"


def load_data():
    """Đọc và validate dữ liệu huấn luyện."""
    if not DATA_PATH.exists():
        print(f"Không tìm thấy file dataset: {DATA_PATH}")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH, encoding="utf-8").dropna() # .dropna() để bỏ các dòng có giá trị NaN. VD: 1 trong 2 cột text/label bị trống.
    df.columns = df.columns.str.strip() # Xóa sạch khoảng trắng thừa (dấu cách, khoảng thụt lề) ở đầu và cuối

    valid_labels = {"SAFETY", "SCAFFOLDING", "KNOWLEDGE_TRACING", "MISCONCEPTION"}
    df = df[df["label"].isin(valid_labels)]

    print(f"Đọc thành công {len(df)} mẫu.")
    print(df["label"].value_counts().to_string())
    return df["text"].tolist(), df["label"].tolist()


def build_pipeline():
    """
    Pipeline học máy: TF-IDF (bigram, bỏ accent chuẩn hóa) + Logistic Regression.
    Dùng Logistic Regression giúp ngưỡng confidence 75% đáng tin cậy hơn.
    """
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),        # Unigram + Bigram
            min_df=1,                  # Giữ lại cả từ xuất hiện ít (dataset nhỏ)
            max_df=0.95,               # Bỏ từ quá phổ biến (xuất hiện > 95% câu)
            sublinear_tf=True,         # Dùng log TF để giảm dominance của từ lặp nhiều
            analyzer="word",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=2.0,                     # Regularization: C cao hơn → fit chặt hơn với data nhỏ
            solver="lbfgs",
            random_state=42,
        )),
    ])


def evaluate(pipeline, X, y):
    """Đánh giá model bằng Stratified K-Fold Cross Validation (5 fold)."""
    print("\n[Đánh giá] Chạy 5-Fold Cross Validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    #n_splits=5: Chia dữ liệu thành 5 phần (gọi là 5 fold).
    #Stratified (Phân tầng): Đảm bảo trong mỗi phần chia, tỉ lệ các nhãn đều bằng nhau (ví dụ: mỗi phần đều có đúng 25% nhãn SAFETY, 25% SCAFFOLDING... tránh trường hợp có phần toàn câu chào hỏi mà không có câu hỏi bài).
    #shuffle=True: Xáo trộn dữ liệu ngẫu nhiên trước khi chia.
    #random_state=42: Cố định cách xáo trộn để lần nào chạy lại kết quả cũng ra y hệt nhau.
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring="accuracy")
    # Nhận về một danh sách 5 kết quả (ví dụ: [0.91, 0.93, 0.90, 0.92, 0.94]).
    print(f"  Độ chính xác trung bình : {scores.mean() * 100:.1f}%")
    print(f"  Độ lệch chuẩn           : ±{scores.std() * 100:.1f}%")
    return scores.mean()


def train_and_save():
    X, y = load_data()
    pipeline = build_pipeline()

    mean_acc = evaluate(pipeline, X, y)
    if mean_acc < 0.70:
        print(f"\n[WARNING] Độ chính xác {mean_acc:.1%} < 70% — cân nhắc thêm dữ liệu.")
    else:
        print(f"\n[OK] Độ chính xác đạt {mean_acc:.1%} — đủ tiêu chuẩn triển khai.")

    # Huấn luyện lại trên TOÀN BỘ dataset (không split)
    print("\n[Training] Huấn luyện trên toàn bộ dataset...")
    pipeline.fit(X, y)

    # Báo cáo chi tiết theo từng intent
    y_pred = pipeline.predict(X) #Cho mô hình vừa học xong làm bài kiểm tra lại: Đọc lại toàn bộ câu hỏi (X) và đưa ra dự đoán của nó (y_pred)
    print("\n[Report - Training Set]")
    print(classification_report(y, y_pred, target_names=sorted(set(y)), zero_division=0))
    # In ra bảng điểm tổng kết chi tiết cho từng loại intent:
    # + Precision: Đoán đúng bao nhiêu %.
    # + Recall: Có bỏ sót câu nào không.
    # + F1-score: Điểm tổng kết chung (càng cao càng tốt).

    # Test nhanh 5 câu mẫu
    test_samples = [
        ("chào thầy ạ",                        "SAFETY"),
        ("em bí rồi thầy ơi giúp em với",      "SCAFFOLDING"),
        ("phân số là gì thầy ơi",              "KNOWLEDGE_TRACING"),
        ("em lấy 1/2 cộng 1/3 bằng 2/5",       "MISCONCEPTION"),
        ("mẫu số chung là gì vậy thầy",        "KNOWLEDGE_TRACING"),
    ]
    print("\n[Smoke Test] Kiểm tra nhanh 5 câu mẫu:")
    all_pass = True
    for text, expected in test_samples:
        proba = pipeline.predict_proba([text])[0] #trả về [SAFETY: 95%, SCAFFOLDING: 2%, KNOWLEDGE_TRACING: 2%, MISCONCEPTION: 1%].
        idx   = proba.argmax() #tìm ra vị trí (index) của con số phần trăm cao nhất
        label = pipeline.classes_[idx] #Danh sách tên các nhãn của mô hình. Dòng này lấy ra tên nhãn có điểm cao nhất
        conf  = proba[idx] #Lấy ra xác suất dự đoán của nhãn cao nhất
        ok    = "✅" if label == expected else "❌"
        if label != expected:
            all_pass = False
        print(f"  {ok} '{text[:45]}'")
        print(f"      Dự đoán: {label} ({conf:.1%})  |  Kỳ vọng: {expected}")

    if all_pass:
        print("\n✅ Tất cả 5 câu smoke test đều đúng!")
    else:
        print("\n⚠️  Có câu smoke test sai — kiểm tra lại dataset.")

    # Lưu model
    joblib.dump(pipeline, MODEL_PATH) #Đóng gói và lưu mô hình AI đã học ra file .pkl để tái sử dụng mà không phải train lại.
    size_kb = MODEL_PATH.stat().st_size / 1024
    print(f"\n✅ Đã lưu model → {MODEL_PATH}  ({size_kb:.1f} KB)")
    print("   Sẵn sàng tích hợp vào OrchestratorAgent (Tầng 1.5).")


if __name__ == "__main__":
    train_and_save()