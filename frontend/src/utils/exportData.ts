import * as XLSX from 'xlsx'

export interface ExportHeader {
  key: string
  label: string
}

/**
 * CSV 字段转义：包含逗号、双引号或换行符时，用双引号包裹
 */
function csvEscape(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n') || value.includes('\r')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * 将行数据按 headers 映射为字符串数组
 */
function rowToValues(row: Record<string, unknown>, headers: ExportHeader[]): string[] {
  return headers.map((h) => {
    const val = row[h.key]
    if (val == null || val === '') return ''
    return String(val)
  })
}

/**
 * 导出 CSV 文件
 * @param headers  列定义（key=字段名, label=中文列名）
 * @param rows     数据行
 * @param filename 文件名（不含路径）
 */
export function exportCsv(headers: ExportHeader[], rows: Record<string, unknown>[], filename: string): void {
  const lines: string[] = []

  // BOM 头，确保 Excel 正确识别 UTF-8 中文
  lines.push('﻿' + headers.map((h) => csvEscape(h.label)).join(','))

  for (const row of rows) {
    lines.push(rowToValues(row, headers).map(csvEscape).join(','))
  }

  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
  downloadBlob(blob, filename)
}

/**
 * 导出 Excel (.xlsx) 文件
 * @param headers  列定义（key=字段名, label=中文列名）
 * @param rows     数据行
 * @param filename 文件名（不含路径）
 */
export function exportExcel(headers: ExportHeader[], rows: Record<string, unknown>[], filename: string): void {
  // 组装二维数组：[表头, ...数据行]
  const aoa: string[][] = [headers.map((h) => h.label)]
  for (const row of rows) {
    aoa.push(rowToValues(row, headers))
  }

  const ws = XLSX.utils.aoa_to_sheet(aoa)

  // 自动列宽：取表头长度和每列最大内容长度的较大值
  ws['!cols'] = headers.map((h, colIdx) => {
    const dataLens = rows.map((r) => String(r[h.key] ?? '').length)
    const maxLen = Math.max(h.label.length, ...dataLens)
    return { wch: Math.min(maxLen + 4, 60) } // 加 padding，上限 60 字符
  })

  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
  XLSX.writeFile(wb, filename)
}

/**
 * 触发浏览器下载 Blob
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
