import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import OrderComposer from './OrderComposer.vue'

describe('OrderComposer', () => {
  it('builds a multi-item cart payload on submit', async () => {
    const wrapper = mount(OrderComposer, {
      props: {
        loading: false,
        selectedFolio: { id: 'f1', room_number: '1208', guest_name: 'Maya Chen' },
      },
    })

    const forms = wrapper.findAll('form')

    await forms[0].trigger('submit.prevent')

    const selects = wrapper.findAll('select')
    await selects[0].setValue('late_checkout_2pm')
    await forms[0].trigger('submit.prevent')

    await forms[1].trigger('submit.prevent')

    const emitted = wrapper.emitted('submit')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0].items).toHaveLength(2)
    expect(emitted[0][0].service_fee).toBe('10.62')
  })

  it('blocks cart submit when delivery window is invalid', async () => {
    const wrapper = mount(OrderComposer, {
      props: {
        loading: false,
        selectedFolio: { id: 'f1', room_number: '1208', guest_name: 'Maya Chen' },
      },
    })

    const forms = wrapper.findAll('form')
    await forms[0].trigger('submit.prevent')

    const datetimeInputs = wrapper.findAll('input[type="datetime-local"]')
    await datetimeInputs[0].setValue('2026-03-29T18:00')
    await datetimeInputs[1].setValue('2026-03-29T17:00')

    await forms[1].trigger('submit.prevent')

    expect(wrapper.emitted('submit')).toBeFalsy()
    expect(wrapper.text()).toContain('Delivery end must be after delivery start.')
  })
})
