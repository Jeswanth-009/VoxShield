# 02 — Listen to VoxShield, and record the live demonstration

**What this page proves:** the actual Windows demo can be heard, not only seen. This is an engineering demonstration using a JBL microphone, the laptop microphone array, and the v15 model. It is **not** a synchronized headset or a field test.

## The two audio stories must stay separate

| Recording | Input | What a judge can conclude |
| --- | --- | --- |
| **Live A/B video** | Speech at JBL mic; noise from a phone near the laptop mic; actual JBL headphone output captured by OBS | The dashboard controls change the sound of a running local audio path. Dry and enhanced portions are different moments, so this is not a sample-identical objective comparison. |
| **Fixed-pair listening clips** | One frozen noisy WAV and its corresponding reference WAV; the same noisy WAV is compared with v15 output | A repeatable before/after comparison. Label source dataset, model version, and whether the mixture was simulated. This is not a live field recording. |

**Audio publication status:** no listening WAVs or live video are included in this QR package yet. Add them only after listening to the files, checking attribution and redistribution rights, and confirming they match the v15 model. Do not use another model's output or an unlabeled sound effect as v15 proof.

## Record the live sound correctly

Use **OBS Studio** on the Windows laptop. The important capture is the *audio sent to the JBL headphones*. A camera pointed at the headset will not capture that cleanly, and adding the JBL microphone directly to OBS would put the raw mic over the enhanced output.

1. Connect the JBL headset. Select its headphones as VoxShield's output device. Keep the JBL microphone close to your mouth; position the phone-noise source near the laptop array. Use one marked phone location and one fixed phone volume.
2. Run `voxshield-live-dual-device --list-devices` or the existing demo helper's device check. Then start [`scripts/run_v15_jbl_dashboard_demo.ps1`](../../scripts/run_v15_jbl_dashboard_demo.ps1) with the current primary, reference and output IDs. The helper defaults to a **disclosed controlled reference mix of 0.30**. If you use it, put `CONTROLLED ELECTRONIC MIX` on screen. Setting the mix to `0` removes this injection; it may make bypass quiet because the JBL input itself can suppress background noise.
3. In OBS, add **Display Capture** or **Window Capture** for the dashboard. Add **Audio Output Capture** and explicitly select the JBL headphones/output endpoint. In OBS *Settings → Audio*, disable a duplicate global Desktop Audio source if it captures the same output. Do **not** add the JBL mic as a second audio source to the judge-facing track. If a separate narrator speaks, record that voice in a different take or track.
4. Say one test sentence while the phone noise is on. Watch the OBS output-capture meter. Record ten seconds, stop, and play the file back **through another device or after VoxShield has stopped**. Confirm that the recorded audio changes when dashboard Dry/Bypass versus Enhanced is selected. If the meter does not move, OBS is listening to the wrong output endpoint.
5. Start the real take. Leave two seconds of untouched raw audio at the beginning, show both input meters, select **Dry/Bypass** and say the sentence, select **Enhanced** and repeat the *same sentence* with the phone in the same marked place. Show the mode change on screen and leave the OBS recording continuous. Do not replace the live audio in editing.
6. At the end, stop the live app and save its session JSON. Keep the original OBS recording, export a short judge-facing MP4, and label the on-screen mode and device topology. If the output is silent, clipping, or the reference gate is not ready, stop and fix it; do not cut around it and call it a successful run.

Suggested sentence: **“Hold position. Left flank clear. Confirm radio check.”** Speak at a consistent distance and level in both modes. Use a fan/engine sample first; use a brief impulse sample only after testing safe playback volume. Avoid very loud sound near your ears.

### OBS track layout

| Track | Source | Purpose |
| --- | --- | --- |
| 1 | JBL **output capture** | Judge-facing sound: exactly what VoxShield sends to the headphones |
| 2, optional | Narration microphone | Editing track; not evidence of enhanced output |
| 3, optional | Phone/sound source captured separately | Context only; never substitute it for the monitored VoxShield output |

For a quick final MP4, keep the JBL output on track 1 so ordinary players can hear it. OBS documents [Audio Output Capture](https://obsproject.com/kb/audio-sources), [initial audio checks](https://obsproject.com/kb/quick-start-guide), and [multiple recording tracks](https://obsproject.com/kb/multiple-audio-track-recording-guide).

## Add fixed-pair clips later

Publish three short groups, each with **Noisy**, **Enhanced v15**, and **Clean target** (only if the clean speech may legally be redistributed). Select one ordinary case, one impulse/mixed case and one hard failure. Align lengths and playback gain; never make only the enhanced file louder. For each group show: audit name and clip ID, category and noise label, whether synthetic or real, source attribution/licence, input SNR, and v15 checkpoint/ONNX hashes. The existing local enhanced examples are in `artifacts/v15-broad-audio/` and `artifacts/v15-military-audio/`; their noisy/reference/clean counterparts are in local `data/mixtures/`, which is intentionally not published.

**Do not upload those dataset-derived clips automatically.** ESC-50 is [CC BY-NC](https://github.com/karolpiczak/ESC-50/blob/master/README.md#license), and the local VCTK corpus carries [ODC-By attribution terms](https://datashare.ed.ac.uk/items/3ea66d32-4541-4cf4-9571-443cc042466b/full). Check each chosen source and attribution first. A new recording made entirely by Team@ is simpler to publish, provided the primary/reference files truly belong to the same capture session.

## The exact video caption to use

> LIVE WINDOWS DUAL-DEVICE ENGINEERING DEMO · JBL voice mic + laptop environmental mic · v15 ONNX · separate device clocks · controlled electronic reference mix **[ON/OFF and value]**

The live demonstration is evidence of the software path. Physical end-to-end latency, synchronized two-microphone hardware, and field intelligibility remain unmeasured.
