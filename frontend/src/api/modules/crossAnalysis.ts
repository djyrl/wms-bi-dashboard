import request from '../request'

export interface ProjectMatrixRes {
  projects: string[]
  project_codes: string[]
  months: string[]
  data: number[][]
  metric: string
  unit: string
}

export interface TopProjectsRes {
  labels: string[]
  values: number[]
  unit: string
}

export interface ProjectTrendRes {
  months: string[]
  series: { name: string; data: number[] }[]
  unit: string
}

export interface SourceDistributionRes {
  labels: string[]
  values: number[]
  unit: string
}

export interface MatrixParams { metric?: string; project_type?: string; months?: number }
export interface TopParams { metric?: string; project_type?: string; limit?: number; group_by?: string }
export interface TrendParams { metric?: string; project_type?: string; months?: number }
export interface SourceParams { project_type?: string }

export const getProjectMatrix = (params?: MatrixParams) =>
  request.get<ProjectMatrixRes>('/wms/indicators/project-matrix', { params })

export const getProjectTypes = () =>
  request.get<string[]>('/wms/indicators/project-types')

export const getTopProjects = (params?: TopParams) =>
  request.get<TopProjectsRes>('/wms/indicators/project-top', { params })

export const getProjectTrend = (params?: TrendParams) =>
  request.get<ProjectTrendRes>('/wms/indicators/project-trend', { params })

export const getSourceDistribution = (params?: SourceParams) =>
  request.get<SourceDistributionRes>('/wms/indicators/source-distribution', { params })
