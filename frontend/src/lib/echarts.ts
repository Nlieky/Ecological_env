import * as echarts from 'echarts/core'
import { BarChart, GraphChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent, DataZoomComponent } from 'echarts/components'
import { LabelLayout, UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart, GraphChart, LineChart, PieChart,
  GridComponent, LegendComponent, TooltipComponent, DataZoomComponent,
  LabelLayout, UniversalTransition,
  CanvasRenderer,
])

export default echarts
