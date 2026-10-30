# TikTo Notification Service

Python service độc lập và không có dependency ngoài standard library. Đây là skeleton để bổ sung database, queue, retry và Telegram/email sau.

Đây là một source/repository riêng, chạy độc lập với web source `TikTo-App`.

## Chạy local

Yêu cầu Python 3.11 trở lên.

```bash
python main.py
```

Service chạy tại `http://localhost:8000`.
Có thể đổi port bằng biến môi trường `PORT`.

## API hiện tại

- `GET /health`
- `GET /notifications`
- `POST /notifications`
- `DELETE /notifications/:id` — đánh dấu notification là `CANCELED`

Ví dụ tạo notification:

```json
{
  "targetType": "TASK",
  "targetId": "task-id",
  "channel": "LOG",
  "message": "Công việc sắp đến hạn",
  "scheduledAt": "2026-10-30T10:00:00Z"
}
```

Dữ liệu hiện lưu trong memory và sẽ mất khi restart. Đây là chủ ý để service giữ tối giản trong giai đoạn đầu.
