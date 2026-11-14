// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import nonPilot from '../../../../backend/tests/fixtures/api/predict_non_pilot.json'
import fixture from '../../../../backend/tests/fixtures/api/predict_seasonal_profile.json'
import type { Schemas } from '@/lib/api'
import GapList from './GapList.vue'
import MonthDetail from './MonthDetail.vue'
import MonthStrip from './MonthStrip.vue'

const predict = fixture as unknown as Schemas['PredictOut']
const outside = nonPilot as unknown as Schemas['PredictOut']

function strip(answer: Schemas['PredictOut']) {
  return mount(MonthStrip, {
    props: { months: answer.months, riskiest: answer.riskiest_month, modelValue: answer.riskiest_month },
  })
}

describe('MonthStrip', () => {
  it('shows the eight months March to October, each with the API word', () => {
    const tiles = strip(predict).findAll('.month-tile')
    expect(tiles).toHaveLength(8)
    expect(tiles[0]!.text()).toContain('Mar')
    expect(tiles[7]!.text()).toContain('Oct')
    tiles.forEach((tile, index) => expect(tile.text()).toContain(predict.months[index]!.label))
  })

  it('pairs every colour with an icon and a word', () => {
    for (const tile of strip(predict).findAll('.month-tile')) {
      expect(tile.attributes('data-level')).toMatch(/^(low|medium|high)$/)
      expect(tile.find('svg').exists()).toBe(true)
    }
  })

  it('marks only the riskiest month', () => {
    const marked = strip(predict)
      .findAll('.month-tile')
      .filter((tile) => tile.text().includes('Riskiest'))
    expect(marked).toHaveLength(1)
    expect(marked[0]!.attributes('data-riskiest')).toBe('true')
    expect(marked[0]!.text()).toContain('Mar')
  })

  it("reads the API's own sentence to screen readers", () => {
    const tiles = strip(predict).findAll('.month-tile')
    tiles.forEach((tile, index) => expect(tile.attributes('aria-label')).toBe(predict.months[index]!.aria_label))
  })

  it('shows no percent sign on the main path', () => {
    expect(strip(predict).text()).not.toContain('%')
    expect(strip(outside).text()).not.toContain('%')
  })

  it('tells the map which month was tapped', async () => {
    const wrapper = strip(predict)
    await wrapper.findAll('.month-tile')[4]!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([7])
  })

  it('renders a field outside the pilot area without errors', () => {
    expect(strip(outside).findAll('.month-tile')).toHaveLength(8)
  })
})

describe('MonthDetail', () => {
  const march = predict.months[0]!
  const detail = mount(MonthDetail, { props: { month: march, cropName: 'Spring barley', needsReview: true } })

  it("uses the API's evidence sentence, word for word", () => {
    expect(detail.find('[data-test=driver]').text()).toBe(march.drivers[0]!.text)
    expect(detail.text()).toContain(march.frequency_text)
  })

  it('keeps the percent and the range behind "More detail"', () => {
    expect(detail.text()).not.toContain('%')
  })
})

describe('GapList', () => {
  it('always shows gaps: the first two, and the rest one tap away', async () => {
    const list = mount(GapList, { props: { gaps: predict.information_gaps } })
    expect(predict.information_gaps.length).toBeGreaterThan(2)
    expect(list.findAll('[data-test=gap]')).toHaveLength(2)
    await list.find('button').trigger('click')
    expect(list.findAll('[data-test=gap]')).toHaveLength(predict.information_gaps.length)
    expect(list.text()).toContain(predict.information_gaps[0]!.text)
  })
})
