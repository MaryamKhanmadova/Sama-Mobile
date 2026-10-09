# Voice microphone and transcript update

Microphone off stops the published MediaStreamTrack synchronously and disables it. The transport mute operation is awaited. The LiveKit audio track uses stopOnMute, so reopening it reacquires capture via the SDK and refreshes the input analyser. Mute/unmute operations are serialized; a failed operation stops capture and closes the call. Ending or unmounting closes pending microphone work before releasing the session. SDK 1.27.0 is pinned because its exported setup hook and input lifecycle were verified in the installed source.

The transcript uses the same message bubbles and horizontal inset as the text composer. It occupies the remaining screen space below the agent and voice controls and scrolls independently. All messages are retained for the current call. The agent area stays in place as messages arrive; shorter screens use compact dimensions. Text chat retains its existing composer.

Validation: production build, microphone capture/transport failure and cancellation tests; browser UI checks with a temporary synthetic voice adapter at 1280×720, 390×844 and 390×667. The synthetic adapter is outside the project and is not shipped. Microphone-off/on icons, silent input bars, 12-message retention, independent scrolling, stable agent position and mobile overflow were checked. Physical-device end-to-end audio mute still needs a live call on the user's microphone; no ambient user audio was transmitted for the browser check.

Backend recheck on 9 October 2026 after the new deployment: health and both documented usage endpoints return 200. All ten demo lines plus summary pass schema validation and return six months through the public proxy. The same original backend API key is used server-side; no new frontend credential is needed.

Product display: Səma Mobile in AZ, Sama Mobile in EN/RU. Agent display: Məryəm Agent in AZ, Maryam Agent in EN/RU. Legacy assistant response text is normalized for display. Spoken voice content is controlled by the configured voice agent.
