export function formatDateTime(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

export function summarizeBrief(brief: string, maxLength: number = 72) {
  if (brief.length <= maxLength) {
    return brief
  }

  return `${brief.slice(0, maxLength - 1).trimEnd()}…`
}
