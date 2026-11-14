<script setup lang="ts">
import SiteHeader from '@/components/site/SiteHeader.vue'
import HeroSection from '@/components/site/HeroSection.vue'
import AudienceShowcase from '@/components/site/AudienceShowcase.vue'
import StatsMarquee from '@/components/site/StatsMarquee.vue'
import HowItWorks from '@/components/site/HowItWorks.vue'
import SiteFooter from '@/components/site/SiteFooter.vue'
</script>

<template>
  <a
    class="skip-link"
    href="#main"
  >Skip to content</a>
  <div class="relative">
    <SiteHeader />
    <main
      id="main"
      tabindex="-1"
      class="outline-none"
    >
      <HeroSection />
      <AudienceShowcase />
      <StatsMarquee />
      <HowItWorks />
    </main>
    <SiteFooter />
  </div>
</template>
