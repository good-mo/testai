<template>
  <MsTag theme="light" :type="getStatusInfo.type"> {{ t(getStatusInfo.label) }}</MsTag>
</template>

<script setup lang="ts">
  import MsTag from '@/components/pure/ms-tag/ms-tag.vue';

  import { useI18n } from '@/hooks/useI18n';

  const { t } = useI18n();
  const props = defineProps<{
    status: string;
  }>();

  // TODO: Record<string,any>
  // 报告步骤状态：覆盖执行结果语义 + 执行生命周期语义，避免后端返回未知值时渲染崩溃
  const statusMap: Record<string, any> = {
    PENDING: {
      label: 'common.unExecute',
      value: 'PENDING',
      type: 'default',
    },
    FAKE_ERROR: {
      label: 'common.fakeError',
      value: 'FAKE_ERROR',
      type: 'warning',
    },
    ERROR: {
      label: 'common.fail',
      value: 'ERROR',
      type: 'danger',
    },
    SUCCESS: {
      label: 'common.pass',
      value: 'SUCCESS',
      type: 'success',
    },
    RUNNING: {
      label: 'common.running',
      value: 'RUNNING',
      type: 'warning',
    },
    COMPLETED: {
      label: 'common.completed',
      value: 'COMPLETED',
      type: 'success',
    },
    RERUNNING: {
      label: 'ms.taskCenter.failRerun',
      value: 'RERUNNING',
      type: 'warning',
    },
    STOPPED: {
      label: 'common.stopped',
      value: 'STOPPED',
      type: 'warning',
    },
  };
  const DEFAULT_STATUS = statusMap.PENDING;

  // 兜底：未知状态统一展示为「未执行」，避免 undefined.label 崩溃
  const getStatusInfo = computed(() => statusMap[props.status] || DEFAULT_STATUS);
</script>

<style scoped></style>
