<template>
  <a-tag
    :color="getExecStatus()?.color"
    :class="getExecStatus()?.class"
    :size="props.size"
  >
    {{ t(getExecStatus()?.label) }}
  </a-tag>
</template>

<script setup lang="ts">
  import { useI18n } from '@/hooks/useI18n';

  import { ReportExecStatus } from '@/enums/apiEnum';
  import { ExecuteStatusEnum } from '@/enums/taskCenter';

  import { executeStatusMap } from './config';

  const props = defineProps<{
    status: ReportExecStatus | ExecuteStatusEnum;
    size?: 'small' | 'medium' | 'large';
  }>();
  const { t } = useI18n();

  const DEFAULT_STATUS = {
    label: 'common.unExecute',
    color: 'var(--color-text-n8)',
    class: '!text-[var(--color-text-1)]',
  };

  function getExecStatus() {
    if (!props.status) {
      return DEFAULT_STATUS;
    }
    return executeStatusMap[props.status] || DEFAULT_STATUS;
  }
</script>

<style lang="less" scoped></style>
