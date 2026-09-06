<template>
  <div ref="chartWrapRef" class="ms-chart-wrap" :style="{ width, height }">
    <VCharts
      v-if="chartId"
      ref="chartRef"
      :option="options"
      :autoresize="autoResize"
      class="ms-chart-inner"
    />
  </div>
</template>

<script lang="ts" setup>
  import { ref } from 'vue';

  import { getGenerateId } from '@/utils';

  import { BarChart, CustomChart, LineChart, PieChart, RadarChart } from 'echarts/charts';
  import {
    DataZoomComponent,
    GraphicComponent,
    GridComponent,
    LegendComponent,
    TitleComponent,
    TooltipComponent,
  } from 'echarts/components';
  import { use } from 'echarts/core';
  import { CanvasRenderer } from 'echarts/renderers';
  import VCharts from 'vue-echarts';

  use([
    CanvasRenderer,
    BarChart,
    CustomChart,
    LineChart,
    PieChart,
    RadarChart,
    GridComponent,
    TooltipComponent,
    LegendComponent,
    DataZoomComponent,
    GraphicComponent,
    TitleComponent,
  ]);

  defineProps({
    options: {
      type: Object,
      default() {
        return {};
      },
    },
    autoResize: {
      type: Boolean,
      default: true,
    },
    width: {
      type: String,
      default: '100%',
    },
    height: {
      type: String,
      default: '100%',
    },
  });

  const chartWrapRef = ref<HTMLDivElement>();
  const chartRef = ref<InstanceType<typeof VCharts>>();
  const chartId = ref('');

  let resizeObserver: ResizeObserver | null = null;
  let fallbackTimer: ReturnType<typeof setTimeout> | null = null;

  function initChart() {
    if (!chartId.value) {
      chartId.value = getGenerateId();
    }
  }

  function cleanup() {
    resizeObserver?.disconnect();
    resizeObserver = null;
    if (fallbackTimer) {
      clearTimeout(fallbackTimer);
      fallbackTimer = null;
    }
  }

  function tryInitChart() {
    const wrapEl = chartWrapRef.value;
    if (wrapEl && !chartId.value && wrapEl.clientWidth > 0 && wrapEl.clientHeight > 0) {
      cleanup();
      initChart();
    }
  }

  onMounted(() => {
    const wrapEl = chartWrapRef.value;
    if (!wrapEl) return;

    // 容器已有尺寸时直接初始化，保持原有即时行为
    if (wrapEl.clientWidth > 0 && wrapEl.clientHeight > 0) {
      initChart();
      return;
    }

    // 容器暂未布局（0尺寸）时，通过 ResizeObserver 等待布局完成后再初始化
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(tryInitChart);
      resizeObserver.observe(wrapEl);
      // 检查一次（ResizeObserver 回调是异步的）
      tryInitChart();
      // 兜底：超时后强制初始化，避免因布局异常导致图表永不渲染
      fallbackTimer = setTimeout(() => {
        cleanup();
        initChart();
      }, 200);
    } else {
      // ResizeObserver 不可用时直接初始化
      initChart();
    }
  });

  onUnmounted(() => {
    cleanup();
    chartId.value = '';
  });

  defineExpose({
    chartRef,
  });
</script>

<style scoped>
  .ms-chart-wrap {
    position: relative;
  }
  .ms-chart-inner {
    width: 100% !important;
    height: 100% !important;
  }
</style>
