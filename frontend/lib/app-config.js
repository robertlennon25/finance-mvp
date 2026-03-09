export const MAX_DOCUMENTS_PER_DEAL = 5;
export const MAX_SINGLE_FILE_BYTES = 20 * 1024 * 1024;
export const MAX_TOTAL_UPLOAD_BYTES = 75 * 1024 * 1024;

export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  return `${value >= 10 ? value.toFixed(0) : value.toFixed(1)} ${units[unitIndex]}`;
}
