<template>
  <div v-if="!licenseStore.hasLicense()" class="mb-2">
    <a-alert type="warning">
      <div class="flex items-center">
        {{ props.tipContent }}
      </div>
    </a-alert>
  </div>
</template>

<script setup lang="ts">
  import useLicenseStore from '@/store/modules/setting/license';

  const licenseStore = useLicenseStore();
  const props = defineProps<{
    tipContent: string;
  }>();

</script>

<style scoped></style>
