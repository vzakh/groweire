import { computed } from 'vue'
import { defineStore } from 'pinia'
import { api, unwrap, useResource, type Schemas } from '@/lib/api'

/** Lists that never change during a visit: crops, map layers, the words we explain. */
export const useCatalogStore = defineStore('catalog', () => {
  const crops = useResource<Schemas['CropsOut']>()
  const layers = useResource<Schemas['LayersOut']>()
  const glossary = useResource<Schemas['GlossaryOut']>()

  function loadCrops() {
    if (crops.data.value || crops.loading.value) return
    return crops.run(() => unwrap(api.GET('/api/v1/crops')))
  }
  function loadLayers() {
    if (layers.data.value || layers.loading.value) return
    return layers.run(() => unwrap(api.GET('/api/v1/layers')))
  }
  function loadGlossary() {
    if (glossary.data.value || glossary.loading.value) return
    return glossary.run(() => unwrap(api.GET('/api/v1/glossary')))
  }

  const cropList = computed(() => crops.data.value?.crops ?? [])
  /** Crops a farmer grows for harvest or grazing. Cover crops are only ever suggested. */
  const mainCrops = computed(() => cropList.value.filter((crop) => crop.role === 'main'))
  const cropById = computed(() => new Map(cropList.value.map((crop) => [crop.id, crop])))
  /** Every market a main crop can be sold into, in catalogue order. */
  const markets = computed(() => [...new Set(mainCrops.value.flatMap((crop) => crop.market))])

  function cropName(id: string): string {
    return cropById.value.get(id)?.name ?? id
  }

  const layerById = computed(() => new Map((layers.data.value?.layers ?? []).map((l) => [l.id, l])))
  const termById = computed(() => new Map((glossary.data.value?.terms ?? []).map((t) => [t.id, t])))

  return {
    crops: crops.data,
    cropsLoading: crops.loading,
    cropsError: crops.error,
    layers: layers.data,
    layersError: layers.error,
    glossary: glossary.data,
    glossaryLoading: glossary.loading,
    glossaryError: glossary.error,
    loadCrops,
    loadLayers,
    loadGlossary,
    cropList,
    mainCrops,
    cropById,
    markets,
    cropName,
    layerById,
    termById,
  }
})
