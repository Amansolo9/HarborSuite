import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import LoginPanel from './LoginPanel.vue'

describe('LoginPanel', () => {
  it('emits submit payload', async () => {
    const wrapper = mount(LoginPanel, { props: { loading: false, error: '' } })
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('guest@seabreeze.local')
    await inputs[1].setValue('Harbor#2026!')

    await wrapper.find('form').trigger('submit.prevent')

    const emitted = wrapper.emitted('submit')
    expect(emitted).toBeTruthy()
    expect(emitted[0][0]).toEqual({ username: 'guest@seabreeze.local', password: 'Harbor#2026!' })
  })

  it('blocks submit when password policy is not met', async () => {
    const wrapper = mount(LoginPanel, { props: { loading: false, error: '' } })
    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('guest@seabreeze.local')
    await inputs[1].setValue('short')

    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.emitted('submit')).toBeFalsy()
    expect(wrapper.text()).toContain('Password must be 10+ chars')
  })
})
