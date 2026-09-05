<template>
  <div class="flex items-center justify-start">
    <MsIcon
      :type="getExecutionResult()?.icon || 'icon-icon_info_outlined'"
      :style="{ color: getExecutionResult()?.color || 'var(--color-text-4)' }"
      size="14"
    />
    <span class="ml-1">{{ t(getExecutionResult()?.label || '-') }}</span>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from '@/hooks/useI18n';

  import { executeResultMap } from './config';

  const { t } = useI18n();
  const props = defineProps<{
    status?: string;
  }>();

  export interface IconType {
    icon: string;
    label: string;
    color?: string;
  }

  function getExecutionResult(): IconType {
    if (!props.status) {
      return executeResultMap.DEFAULT;
    }
    return executeResultMap[props.status] ? executeResultMap[props.status] : executeResultMap.DEFAULT;
  }
</script>

<style scoped></style>
