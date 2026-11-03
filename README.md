# TikTo Notification Service

Notification service độc lập, hiện dùng Python standard library và lưu dữ liệu trong memory. Service không truy cập database hoặc cần AWS credential.

## Chạy local

Yêu cầu Python 3.11 trở lên.

```bash
python main.py
```

Service chạy tại `http://localhost:8000` và mặc định lưu notification trong memory.

Để health check nhận diện tài khoản notification, cấu hình hai biến môi trường không chứa secret:

```text
NOTIFICATION_PROVIDER=telegram
NOTIFICATION_ACCOUNT_NAME=@tikto_bot
```

`GET /health` trả `account.connected: true` khi cả provider và account name đã được cấu hình. Token, password và secret không được trả về API.

## API

- `GET /health` — kiểm tra service, version và tài khoản notification
- `GET /notifications`
- `POST /notifications`
- `DELETE /notifications/:id` — đánh dấu `CANCELED`

Ví dụ tạo notification:

```json
{
  "targetType": "TASK",
  "targetId": "task-id",
  "channel": "LOG",
  "message": "Công việc sắp đến hạn",
  "scheduledAt": "2026-10-31T10:00:00Z"
}
```

## CI/CD

Tạo pull request thủ công từ branch làm việc vào `dev`. CI kiểm tra merge result; mọi pull request hợp lệ trong cùng repository và có base là `dev` sẽ được squash-merge sau khi CI thành công. Thay đổi chỉ liên quan tài liệu sẽ bỏ qua job format, lint, test và compile tốn tài nguyên.

Mỗi merge vào `dev` tạo image immutable `dev-<commit>`. Production không dùng branch `main`: chạy workflow **Release production** từ `dev` với semantic version mới, ví dụ `v1.2.3`. Workflow kiểm tra source, chờ duyệt trong GitHub Environment `prod`, promote đúng development image sang version đó, quét lại bằng Trivy và tạo GitHub Release immutable. SonarQube được tự động phân tích bên ngoài GitHub Actions.

Cấu hình các GitHub organization/repository settings:

- Đặt `dev` làm default branch; bắt buộc các check của `CI` pass và branch phải up-to-date trước khi merge.
- Bật repository auto-merge.
- Cho phép GitHub Actions workflow có quyền read/write để job auto-merge cập nhật pull request.
- Variable `AWS_BUILD_ROLE_ARN`: Terraform output `github_build_role_arn` của shared stack.
- Variable `AWS_REGION`: `ap-southeast-2`.
- Bảo vệ GitHub Environment `prod` bằng required reviewers.
