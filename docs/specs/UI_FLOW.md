# UI Flow Specification

## User Pages

### 1. Login Page

Path:
```text
/login
```

Fields:
```text
Secret key
```

Actions:
```text
Login
```

Behavior:
- If key valid, store access token and redirect to dashboard.
- If invalid, show error.
- Do not show whether user exists.

### 2. User Dashboard

Path:
```text
/dashboard
```

Shows:
```text
- Upload new video button
- Recent jobs
- Job status badges
- Quota summary if available
```

### 3. Create Job / Upload Page

Path:
```text
/jobs/new
```

Fields:
```text
video file
```

Validation:
```text
- required
- max 500MB
- allowed extension: mp4, mov, mkv, webm
```

Flow:
```text
1. User selects video.
2. Click Start.
3. Web calls POST /jobs.
4. If node available, web receives upload_url + upload_token.
5. Browser uploads file directly to node.
6. Web shows upload progress.
7. Web calls start processing if needed.
8. Redirect to /jobs/{id}.
```

If no node:
```text
Show: "Hiện chưa có VPS rảnh. Vui lòng thử lại sau."
```

### 4. Job Progress Page

Path:
```text
/jobs/[jobId]
```

Shows:
```text
- current status
- progress bar
- current step
- node name if allowed
- error message if failed
- download button if done
```

Status labels:
```text
WAITING_UPLOAD: Đang chờ upload
UPLOADING: Đang tải video lên VPS
EXTRACTING_AUDIO: Đang tách âm thanh
TRANSCRIBING: Đang nhận diện tiếng Trung
TRANSLATING: Đang dịch sang tiếng Việt
GENERATING_SRT: Đang tạo subtitle
RENDERING: Đang render video
DONE: Hoàn tất
FAILED: Lỗi
```

### 5. Job History

Path:
```text
/jobs
```

Shows:
```text
- job id short
- filename
- status
- created time
- completed time
- action
```

## Admin Pages

### 1. Admin Dashboard

Path:
```text
/admin
```

Cards:
```text
- total users
- active jobs
- idle nodes
- busy nodes
- offline nodes
- failed jobs today
```

### 2. Users

Path:
```text
/admin/users
```

Actions:
```text
- create user
- issue key
- revoke key
- block/unblock user
```

Important:
- Secret key is shown only once when generated.

### 3. VPS Nodes

Path:
```text
/admin/nodes
```

Table:
```text
name
public_url
status
current_job
cpu
ram
disk_free
last_heartbeat
enabled
actions
```

Actions:
```text
- add node
- generate install command
- disable node
- enable node
- remove node
```

### 4. Node Detail

Path:
```text
/admin/nodes/[nodeId]
```

Shows:
```text
- health
- resource stats
- current job
- recent heartbeats
- agent version
- install command
```

### 5. Jobs

Path:
```text
/admin/jobs
```

Filters:
```text
status
user
node
date
```

Actions:
```text
view details
cancel
retry later
```

### 6. Job Detail

Path:
```text
/admin/jobs/[jobId]
```

Shows:
```text
- metadata
- user
- node
- status timeline
- error message
- job events
- download link if available
```
