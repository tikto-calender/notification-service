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

Pull request vào `dev` hoặc `main` chạy format, lint, unit test và coverage. Push vào hai branch này chạy lại quality gate, build container, dùng Trivy chặn lỗ hổng HIGH/CRITICAL có bản sửa, sau đó push image immutable lên Amazon ECR. SonarQube được tự động phân tích bên ngoài GitHub Actions workflow.

Cấu hình các GitHub organization/repository settings:

- Variable `AWS_BUILD_ROLE_ARN`: Terraform output `github_build_role_arn` của shared stack.
- Variable `AWS_REGION`: `ap-southeast-2`.
