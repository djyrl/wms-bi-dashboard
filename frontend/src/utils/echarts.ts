import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, FunnelChart, GaugeChart, TreemapChart, HeatmapChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  VisualMapComponent,
  MarkLineComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

/**
 * 按需注册 ECharts 图表类型和组件（tree-shaking）
 * 仅注册 BI Dashboard 用到的：
 *   - 图表: Bar, Line, Pie, Funnel
 *   - 组件: Grid, Tooltip, Legend, Title
 *   - 渲染器: Canvas
 */
export function initECharts() {
  echarts.use([
    BarChart,
    LineChart,
    PieChart,
    FunnelChart,
    GaugeChart,
    TreemapChart,
    HeatmapChart,
    ScatterChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    TitleComponent,
    VisualMapComponent,
    MarkLineComponent,
    CanvasRenderer,
  ])
}

export { echarts }
