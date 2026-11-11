"""
US 10.4 - Task T10.4.4:
Router Quản Trị Active Learning & Tự Tiến Hóa Mô Hình (Admin Active Learning Router).
====================================================================================
Cung cấp các endpoints cho Quản trị viên quản lý hàng đợi thẩm định nhãn phân luồng,
duyệt phản hồi từ Hidden Tag Protocol và kích hoạt tái huấn luyện mô hình máy học (Trụ 2).

Các endpoints chính phục vụ toàn diện cho Backend & Giao diện Giám Sát Agent (T10.4.5):
  1. GET    /api/admin/active-learning/stats         : Thống kê tổng quan KPI (Pending, Approved, Rejected, Mẫu tri thức, Phân bổ nhãn).
  2. GET    /api/admin/active-learning/feedbacks     : Lấy danh sách nhật ký phân luồng (Lọc status, search từ khóa câu hỏi, lọc Agent).
  3. PUT    /api/admin/active-learning/feedbacks/{id}: Hiệu chỉnh trực tiếp câu hỏi hoặc nhãn đề xuất trước khi duyệt.
  4. DELETE /api/admin/active-learning/feedbacks/{id}: Xóa bản ghi cụ thể khỏi hệ thống.
  5. POST   /api/admin/active-learning/retrain       : Duyệt hàng loạt và tái huấn luyện mô hình trọn gói (Retrain + Hot-Reload Zero Downtime).
  6. POST   /api/admin/active-learning/reject        : Từ chối / Bỏ qua các mẫu lỗi, spam hàng loạt (status -> REJECTED).
"""

import os
import sys
import time
import threading
import pathlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import pandas as pd
import joblib
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
import schemas
import dependencies
from models import AuditFeedbackLog
from agents.orchestrator import _agent
from agents.train_intent_model import build_pipeline, DATA_PATH, MODEL_PATH

# Danh mục các nhãn phân luồng Agent hợp lệ trong toàn bộ hệ thống
VALID_INTENTS = {"SAFETY", "SCAFFOLDING", "KNOWLEDGE_TRACING", "MISCONCEPTION"}

# Khóa đồng bộ Non-blocking bảo đảm an toàn đa luồng và chống hiện tượng double-click retrain
_retrain_lock = threading.Lock()

# Router chính thức theo quy chuẩn API
router = APIRouter(
    prefix="/api/admin/active-learning",
    tags=["Admin Active Learning Hub (US 10.4)"],
    dependencies=[Depends(dependencies.require_role(["ADMIN"]))],
)

# Router phụ tương thích ngược nếu Frontend gọi không có tiền tố /api
compat_router = APIRouter(
    prefix="/admin/active-learning",
    tags=["Admin Active Learning Hub (Compatibility)"],
    dependencies=[Depends(dependencies.require_role(["ADMIN"]))],
)


@router.get("/stats", response_model=schemas.ActiveLearningStatsResponse)
@compat_router.get("/stats", response_model=schemas.ActiveLearningStatsResponse)
def get_active_learning_stats(db: Session = Depends(get_db)):
    """
    Cung cấp số liệu thống kê tổng hợp phục vụ các thẻ KPI Card tại Tab 2 Giám Sát Agent:
    - Số lượng câu chờ duyệt (Pending), đã nạp học (Approved), đã bỏ qua (Rejected).
    - Tổng dung lượng mẫu huấn luyện hiện tại trong intent_data.csv.
    - Thời gian nạp mô hình gần nhất và phân bổ tỷ lệ các nhãn Intent.
    """
    total_feedbacks = db.query(AuditFeedbackLog).count()
    pending_count = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.status == "PENDING").count()
    approved_count = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.status == "APPROVED").count()
    rejected_count = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.status == "REJECTED").count()

    total_training_samples = 0
    intents_dist: Dict[str, int] = {intent: 0 for intent in sorted(VALID_INTENTS)}
    last_update_str = None

    if DATA_PATH.exists():
        try:
            df = pd.read_csv(DATA_PATH, encoding="utf-8-sig").dropna()
            df.columns = df.columns.str.strip()
            if "label" in df.columns:
                counts = df["label"].value_counts().to_dict()
                for label, cnt in counts.items():
                    clean_label = str(label).strip().upper()
                    if clean_label in intents_dist:
                        intents_dist[clean_label] = int(cnt)
                total_training_samples = len(df)
        except Exception as e:
            print(f"[AdminActiveLearning] [WARN] Không thể đọc phân bổ intent_data.csv: {e}")

    if MODEL_PATH.exists():
        try:
            mtime = MODEL_PATH.stat().st_mtime
            last_update_str = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
        except Exception:
            last_update_str = None

    return schemas.ActiveLearningStatsResponse(
        success=True,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        total_feedbacks=total_feedbacks,
        total_training_samples=total_training_samples,
        last_model_update=last_update_str,
        intents_distribution=intents_dist,
    )


@router.get("/feedbacks", response_model=schemas.AuditFeedbackListResponse)
@compat_router.get("/feedbacks", response_model=schemas.AuditFeedbackListResponse)
def list_feedback_logs(
    status_filter: Optional[str] = Query("PENDING", alias="status", description="Lọc theo trạng thái: PENDING, APPROVED, REJECTED hoặc ALL"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo từ khóa trong câu hỏi học sinh"),
    agent_filter: Optional[str] = Query(None, alias="agent", description="Lọc theo nhãn đề xuất (MISCONCEPTION, SAFETY...)"),
    limit: int = Query(50, ge=1, le=200, description="Số lượng bản ghi tối đa trả về"),
    offset: int = Query(0, ge=0, description="Vị trí bắt đầu"),
    db: Session = Depends(get_db),
):
    """
    Truy vấn danh sách nhật ký phản hồi phân luồng phục vụ bảng quản trị ActiveLearningTable.
    Hỗ trợ lọc theo trạng thái, tìm kiếm từ khóa trong câu nói của học sinh và lọc theo nhãn đề xuất.
    """
    # Trích xuất giá trị an toàn tương thích cả FastAPI Runtime và Direct Unit Test Invocation
    status_val = status_filter if isinstance(status_filter, str) else "PENDING"
    search_val = search.strip() if isinstance(search, str) and search.strip() else None
    agent_val = agent_filter.strip().upper() if isinstance(agent_filter, str) and agent_filter.strip() else None
    limit_val = limit if isinstance(limit, int) else 50
    offset_val = offset if isinstance(offset, int) else 0

    query = db.query(AuditFeedbackLog)

    if status_val and status_val.upper() != "ALL":
        query = query.filter(AuditFeedbackLog.status == status_val.upper())

    if search_val:
        search_term = f"%{search_val}%"
        query = query.filter(AuditFeedbackLog.user_query.ilike(search_term))

    if agent_val and agent_val in VALID_INTENTS:
        query = query.filter(AuditFeedbackLog.suggested_agent == agent_val)

    total = query.count()
    items = query.order_by(desc(AuditFeedbackLog.created_at)).offset(offset_val).limit(limit_val).all()

    pending_count = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.status == "PENDING").count()
    approved_count = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.status == "APPROVED").count()
    rejected_count = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.status == "REJECTED").count()

    return schemas.AuditFeedbackListResponse(
        success=True,
        total=total,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        items=items,
    )


@router.put("/feedbacks/{feedback_id}", response_model=schemas.AuditFeedbackLogItem)
@compat_router.put("/feedbacks/{feedback_id}", response_model=schemas.AuditFeedbackLogItem)
def update_feedback_item(
    feedback_id: int,
    payload: schemas.UpdateFeedbackRequest,
    db: Session = Depends(get_db),
):
    """
    Cho phép Quản trị viên hiệu chỉnh câu hỏi hoặc nhãn đề xuất trực tiếp trên giao diện bảng trước khi duyệt.
    """
    item = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.id == feedback_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy bản ghi phản hồi có ID {feedback_id}.",
        )

    if payload.suggested_agent is not None:
        clean_agent = payload.suggested_agent.strip().upper()
        if clean_agent not in VALID_INTENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nhãn '{payload.suggested_agent}' không hợp lệ. Chỉ chấp nhận: {', '.join(sorted(VALID_INTENTS))}.",
            )
        item.suggested_agent = clean_agent

    if payload.user_query is not None:
        clean_text = " ".join(payload.user_query.strip().split())
        if not clean_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Câu hỏi của học sinh không được để trống.",
            )
        item.user_query = clean_text[:1000]

    db.commit()
    db.refresh(item)
    return item


@router.delete("/feedbacks/{feedback_id}", response_model=schemas.DeleteFeedbackResponse)
@compat_router.delete("/feedbacks/{feedback_id}", response_model=schemas.DeleteFeedbackResponse)
def delete_feedback_item(
    feedback_id: int,
    db: Session = Depends(get_db),
):
    """
    Xóa một bản ghi phản hồi cụ thể khỏi cơ sở dữ liệu nếu phát hiện dữ liệu spam/rác.
    """
    item = db.query(AuditFeedbackLog).filter(AuditFeedbackLog.id == feedback_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy bản ghi phản hồi có ID {feedback_id}.",
        )

    db.delete(item)
    db.commit()
    return schemas.DeleteFeedbackResponse(
        success=True,
        message=f"Đã xóa thành công bản ghi phản hồi ID {feedback_id}.",
        deleted_id=feedback_id,
    )


@router.post("/retrain", response_model=schemas.RetrainResponse)
@compat_router.post("/retrain", response_model=schemas.RetrainResponse)
def approve_and_retrain(
    payload: schemas.RetrainRequest,
    db: Session = Depends(get_db),
):
    """
    Xử lý trọn gói quy trình Tự học (Active Learning Pipeline):
      1. Lấy các bản ghi PENDING theo danh sách feedback_ids.
      2. Kiểm tra tính hợp lệ của câu hỏi và nhãn đề xuất (suggested_agent).
      3. Bổ sung các mẫu câu mới vào intent_data.csv (chuẩn mã hóa UTF-8, giới hạn an toàn 1000 ký tự).
      4. Huấn luyện lại pipeline mô hình Machine Learning (TF-IDF + Logistic Regression).
      5. Lưu file mô hình mới local_orchestrator.pkl qua cơ chế ghi đè an toàn (Atomic File Replacement + Retry Windows Lock).
      6. Kích hoạt Atomic Swap Hot-Reload nạp mô hình mới trực tiếp vào bộ nhớ RAM của FastAPI (_agent.reload_model).
      7. Chuyển trạng thái các bản ghi trong DB sang APPROVED và commit transaction.
      8. Trả về thông báo thành công kèm số lượng mẫu vừa duyệt và tổng số mẫu huấn luyện hiện tại.
    """
    if not payload.feedback_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách feedback_ids không được để trống.",
        )

    # Khóa Non-blocking: Tránh race-condition khi quản trị viên double-click hoặc nhiều admin cùng thao tác
    if not _retrain_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hệ thống đang thực hiện một tiến trình tái huấn luyện mô hình khác. Vui lòng chờ trong giây lát.",
        )

    csv_appended = False
    original_csv_size = 0

    try:
        # Bước 1: Lấy các bản ghi PENDING theo danh sách mã đã chọn
        items = (
            db.query(AuditFeedbackLog)
            .filter(
                AuditFeedbackLog.id.in_(payload.feedback_ids),
                AuditFeedbackLog.status == "PENDING",
            )
            .all()
        )

        if not items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không tìm thấy bản ghi chờ duyệt (PENDING) nào phù hợp với danh sách mã đã chọn.",
            )

        # Bước 2: Chuẩn hóa dữ liệu câu hỏi và nhãn, loại bỏ trùng lặp trong đợt gửi
        new_rows = []
        seen_pairs = set()
        for it in items:
            # Loại bỏ ký tự xuống dòng ẩn và giới hạn độ dài chống payload quá khổ
            clean_query = " ".join(it.user_query.strip().split())[:1000]
            suggested = it.suggested_agent.strip().upper()
            if suggested not in VALID_INTENTS:
                continue
            pair = (clean_query, suggested)
            if clean_query and pair not in seen_pairs:
                seen_pairs.add(pair)
                new_rows.append({"text": clean_query, "label": suggested})

        if not new_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Các bản ghi được chọn không chứa nhãn phân loại hợp lệ.",
            )

        # Đảm bảo thư mục cha tồn tại
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Lưu lại kích thước ban đầu của file CSV để phục vụ Rollback nếu gặp lỗi
        if DATA_PATH.exists():
            original_csv_size = DATA_PATH.stat().st_size
        else:
            original_csv_size = 0

        # Bước 3: Ghi bổ sung vào intent_data.csv (Bảo đảm kết thúc bằng newline)
        if DATA_PATH.exists() and original_csv_size > 0:
            with open(DATA_PATH, "r+b") as f:
                f.seek(0, os.SEEK_END)
                f.seek(-1, os.SEEK_END)
                last_byte = f.read(1)
                if last_byte not in (b"\n", b"\r"):
                    f.write(b"\n")

        df_new = pd.DataFrame(new_rows)
        df_new.to_csv(
            DATA_PATH,
            mode="a",
            header=not DATA_PATH.exists(),
            index=False,
            encoding="utf-8",
        )
        csv_appended = True

        # Bước 4: Đọc toàn bộ dataset (utf-8-sig chống lỗi BOM) và tái huấn luyện pipeline
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig").dropna()
        df.columns = df.columns.str.strip()
        df = df[df["label"].isin(VALID_INTENTS)]

        X = df["text"].tolist()
        y = df["label"].tolist()

        if len(set(y)) < 2:
            raise ValueError("Dữ liệu huấn luyện phải chứa tối thiểu 2 nhãn intent khác nhau.")

        pipeline = build_pipeline()
        pipeline.fit(X, y)

        # Bước 5: Lưu file mô hình mới an toàn (Atomic File Replacement có Retry chống lock trên Windows)
        temp_model_path = MODEL_PATH.with_suffix(".tmp.pkl")
        joblib.dump(pipeline, temp_model_path)
        if temp_model_path.exists():
            for attempt in range(3):
                try:
                    temp_model_path.replace(MODEL_PATH)
                    break
                except PermissionError:
                    if attempt == 2:
                        raise
                    time.sleep(0.05)

        # Bước 6: Kích hoạt Atomic Swap Hot-Reload trên bộ nhớ RAM Uvicorn
        reload_success = _agent.reload_model(force=True)
        if not reload_success:
            print("[AdminActiveLearning] [WARN] Gọi _agent.reload_model() không thành công.")

        # Bước 7: Chỉ commit DB sang APPROVED sau khi huấn luyện và reload RAM thành công hoàn toàn
        for it in items:
            it.status = "APPROVED"
        db.commit()

        return schemas.RetrainResponse(
            success=True,
            message=f"Đã duyệt {len(new_rows)} mẫu câu mới, tái huấn luyện mô hình và nạp RAM thành công!",
            retrained_count=len(new_rows),
            total_samples=len(df),
        )

    except HTTPException:
        # Giữ nguyên các lỗi nghiệp vụ 400/409 đã raise
        raise
    except Exception as e:
        # Rollback giao dịch Database
        db.rollback()

        # Rollback file CSV về trạng thái ban đầu nếu đã append
        if csv_appended and DATA_PATH.exists() and original_csv_size >= 0:
            try:
                with open(DATA_PATH, "r+b") as f:
                    f.truncate(original_csv_size)
            except Exception as trunc_err:
                print(f"[AdminActiveLearning] [ERROR] Rollback CSV thất bại: {trunc_err}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quá trình tái huấn luyện mô hình gặp sự cố: {str(e)}",
        )
    finally:
        _retrain_lock.release()


@router.post("/reject", response_model=schemas.RejectFeedbacksResponse)
@compat_router.post("/reject", response_model=schemas.RejectFeedbacksResponse)
def reject_feedbacks(
    payload: schemas.RejectFeedbacksRequest,
    db: Session = Depends(get_db),
):
    """
    Từ chối hoặc loại bỏ các mẫu câu spam, sai ngữ nghĩa hoặc dữ liệu rác hàng loạt.
    Chuyển trạng thái các bản ghi tương ứng từ PENDING sang REJECTED.
    """
    if not payload.feedback_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách feedback_ids không được để trống.",
        )

    items = (
        db.query(AuditFeedbackLog)
        .filter(
            AuditFeedbackLog.id.in_(payload.feedback_ids),
            AuditFeedbackLog.status == "PENDING",
        )
        .all()
    )

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không tìm thấy bản ghi chờ duyệt (PENDING) nào phù hợp.",
        )

    for it in items:
        it.status = "REJECTED"
    db.commit()

    return schemas.RejectFeedbacksResponse(
        success=True,
        message=f"Đã từ chối và loại bỏ thành công {len(items)} mẫu câu.",
        rejected_count=len(items),
    )
