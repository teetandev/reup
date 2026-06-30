export const STATUS_LABELS: Record<string, string> = {
  CREATED: 'Đã tạo',
  ASSIGNED_NODE: 'Đã gán VPS',
  WAITING_UPLOAD: 'Đang chờ upload',
  UPLOADING: 'Đang tải video lên VPS',
  UPLOADED: 'Đã tải lên',
  EXTRACTING_AUDIO: 'Đang tách âm thanh',
  CHUNKING_AUDIO: 'Đang chia âm thanh',
  TRANSCRIBING: 'Đang nhận diện tiếng Trung',
  TRANSLATING: 'Đang dịch sang tiếng Việt',
  GENERATING_SRT: 'Đang tạo subtitle',
  RENDERING: 'Đang render video',
  DONE: 'Hoàn tất',
  FAILED: 'Lỗi',
  CANCELLED: 'Đã hủy',
  EXPIRED: 'Đã hết hạn',
};

/** Canonical pipeline step order for the job-detail timeline. */
export const PIPELINE_STEPS: string[] = [
  'WAITING_UPLOAD',
  'UPLOADING',
  'UPLOADED',
  'EXTRACTING_AUDIO',
  'CHUNKING_AUDIO',
  'TRANSCRIBING',
  'TRANSLATING',
  'GENERATING_SRT',
  'RENDERING',
  'DONE',
];

export const TERMINAL_STATUSES = ['DONE', 'FAILED', 'CANCELLED', 'EXPIRED'];

export const PROGRESS_MAP: Record<string, number> = {
  CREATED: 0,
  ASSIGNED_NODE: 5,
  WAITING_UPLOAD: 10,
  UPLOADING: 15,
  UPLOADED: 20,
  EXTRACTING_AUDIO: 30,
  CHUNKING_AUDIO: 40,
  TRANSCRIBING: 50,
  TRANSLATING: 65,
  GENERATING_SRT: 80,
  RENDERING: 90,
  DONE: 100,
  FAILED: 0,
  CANCELLED: 0,
  EXPIRED: 0,
};
