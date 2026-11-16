import type { RouteLocationRaw } from 'vue-router'
import { answersToQuery, type Answers } from './query'
import type { LngLat } from './geo'

/**
 * "Explore an example farm" (`/app?farm=sample`): a 10 ha tillage field near Athlone, with
 * answers already given, opened on the answer step. Same answers as the recorded sample
 * (backend/app/jobs/export_fixtures.py), so mock mode and the real API agree.
 */
export const EXAMPLE_FARM = {
  name: 'Example farm near Athlone',
  point: [-7.995, 53.395] as LngLat,
  areaHa: 10,
  answers: {
    crops: ['spring_barley', 'spring_barley', 'spring_barley', 'spring_barley'],
    priorities: ['income_stability', 'simplicity', 'soil_cover'],
    livestock: false,
    contracts: ['malting_barley'],
    excluded: ['potatoes'],
  } satisfies Answers,
}

/** Where to go once the example field exists: its answer step, answers filled in. */
export function exampleFarmRoute(fieldId: string): RouteLocationRaw {
  return {
    name: 'field',
    params: { id: fieldId, section: '' },
    query: { s: '4', ...answersToQuery(EXAMPLE_FARM.answers) },
  }
}
