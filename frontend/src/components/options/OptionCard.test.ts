// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import cropsFixture from '../../../../backend/tests/fixtures/api/crops.json'
import fixture from '../../../../backend/tests/fixtures/api/rotations_compare.json'
import { copy } from '@/copy/en'
import type { Schemas } from '@/lib/api'
import OptionCard from './OptionCard.vue'

const compared = fixture as unknown as Schemas['CompareOut']
const crops = new Map((cropsFixture as unknown as Schemas['CropsOut']).crops.map((crop) => [crop.id, crop]))

function card(strategy: Schemas['Strategy']) {
  return mount(OptionCard, {
    props: { strategy, crops, provenance: compared.provenance, weights: compared.weights_used },
    // Collapsed content is not rendered; open it so the blocks can be checked
    global: { stubs: { CollapsibleContent: { template: '<div><slot /></div>' } } },
  })
}

const current = compared.strategies.find((s) => s.is_current)!
const alternative = compared.strategies.find((s) => !s.is_current)!

describe('OptionCard', () => {
  it('compares at least three rotations, the current one included', () => {
    expect(compared.strategies.length).toBeGreaterThanOrEqual(3)
    expect(current).toBeDefined()
  })

  it("shows the API's headline and one-line why", () => {
    const wrapper = card(alternative)
    expect(wrapper.find('[data-test=option-headline]').text()).toBe(alternative.headline)
    expect(wrapper.text()).toContain(alternative.one_line_why)
  })

  it('marks the current rotation as the starting point, with no comparison against itself', () => {
    const wrapper = card(current)
    expect(wrapper.text()).toContain(copy.options.yours)
    expect(wrapper.text()).toContain(copy.options.startingPoint)
    expect(wrapper.find('[data-test=vs-current]').exists()).toBe(false)
  })

  it('compares an alternative on risk, bare soil and work, in words', () => {
    const rows = card(alternative).findAll('[data-test=vs-current] li')
    expect(rows).toHaveLength(3)
    expect(rows[0]!.text()).toContain('Risk')
    rows.forEach((row) => expect(row.find('svg').exists()).toBe(true))
  })

  it('has the five explanation blocks', () => {
    const text = card(alternative).find('[data-test=why-blocks]').text()
    for (const title of Object.values(copy.options.blocks)) expect(text).toContain(title)
    expect(text).toContain(alternative.explanation.why_suggested)
  })

  it('ends with two to four questions for the advisor, and the "you decide" line', () => {
    for (const strategy of compared.strategies) {
      const wrapper = card(strategy)
      const questions = wrapper.findAll('[data-test=advisor-questions] li')
      expect(questions.length).toBeGreaterThanOrEqual(2)
      expect(questions.length).toBeLessThanOrEqual(4)
      expect(wrapper.find('[data-test=disclaimer]').text()).toBe(copy.disclaimer)
    }
  })

  it('never shows a score or a percent', () => {
    for (const strategy of compared.strategies) {
      const text = card(strategy).text()
      expect(text).not.toContain('%')
      expect(text).not.toContain(String(strategy.score))
    }
  })

  describe('crop-rule chip', () => {
    const withRules = (rules: Schemas['RuleCompliance']) =>
      card({ ...alternative, metrics: { ...alternative.metrics, rule_compliance: rules } })

    it('says the rules are met', () => {
      const wrapper = withRules({ ie_crop_rotation_2_of_4: true, two_crop_rule_10_30ha: true })
      expect(wrapper.find('[data-test=rule-chip]').text()).toBe(copy.options.rules.ok)
      expect(wrapper.find('[data-test=rule-unknown]').exists()).toBe(false)
    })

    it('says to check the rules', () => {
      const wrapper = withRules({ ie_crop_rotation_2_of_4: false, two_crop_rule_10_30ha: true })
      expect(wrapper.find('[data-test=rule-chip]').text()).toBe(copy.options.rules.check)
    })

    it('says what was not checked when the tillage area is unknown', () => {
      const wrapper = withRules({ ie_crop_rotation_2_of_4: true, two_crop_rule_10_30ha: null })
      expect(wrapper.find('[data-test=rule-unknown]').text()).toBe(copy.options.rules.unknown)
    })
  })
})
