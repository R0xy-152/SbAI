## TV-02

Status: PASS_WITH_LIMITATION

Date: 2026-08-14

Environment: Static frontend, Node.js v24.18.0 DOM simulation.

Goal: Verify that deterministic presentation directives trigger finite, named character effects.

Test cases:

1. Call `window.galPresentation.apply({ character: "deepseek", animation: "fade_in" })`.
2. Call `window.galPresentation.apply({ character: "deepseek", animation: "fade_out" })`.
3. Call `window.galPresentation.apply({ character: "deepseek", animation: "shake" })`.
4. Set the `normal` and `alert` visual states.
5. Submit an unsupported animation name and verify rejection.

Observed result: The automated DOM simulation verifies all named actions map to their corresponding CSS classes, both visual states apply, completed animations clean up their transient classes, and an unsupported action is rejected.

Failures: None observed.

Known limitations:

- Directives are an in-page TV fixture, exposed as `window.galPresentation.apply`; TV-03 will replace the source of directives with a backend round trip.
- Browser animation frames could not be independently inspected because browser automation cannot start in this environment.

Evidence: `node frontend/tests/tv02-presentation.test.cjs`

Conclusion: PASS_WITH_LIMITATION.
