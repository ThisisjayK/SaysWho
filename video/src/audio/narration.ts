import { TIMELINE } from "../film/timing";
import type { Narration } from "./Soundtrack";

/**
 * The voice track, positioned the way the effect cues are: scene plus offset,
 * never an absolute frame.
 *
 * SOUND.md carried absolute timings for one retime too many. The browser scene
 * landed, every line after the title moved by twenty nine seconds, and the table
 * was silently wrong until somebody recomputed it by hand. Anchored to a scene,
 * a retime carries its own narration with it.
 *
 * Offsets are measured, not estimated. Each line was generated first, its real
 * duration read off the file, and the next line placed at least 0.35s after the
 * previous one ends. Three written lines are absent on purpose: see SOUND.md.
 */

const sceneStart = (name: string) => TIMELINE.find((s) => s.name === name)?.start ?? 0;
const beat = (scene: string, offset: number) => sceneStart(scene) + offset;

export const NARRATION: Narration[] = [
  { file: "vo-01.mp3", at: beat("Cold open", 72), note: " Every AI answer now arrives with its sources attached." },
  { file: "vo-02.mp3", at: beat("Cold open", 186), note: " The links are what make it feel checked." },
  { file: "vo-03.mp3", at: beat("Cold open", 288), note: " They are also the part nobody opens." },
  { file: "vo-04.mp3", at: beat("Cold open", 384), note: " And nothing that produced this answer ever read them." },
  { file: "vo-05.mp3", at: beat("Title", 60), note: " SaysWho reads them." },
  { file: "vo-06.mp3", at: beat("In the browser", 105), note: " It runs on the page the answer is already on." },
  { file: "vo-07.mp3", at: beat("In the browser", 270), note: " It takes the answer, hashes it, and lists every source it cites." },
  { file: "vo-08.mp3", at: beat("In the browser", 405), note: " It tells you when it cannot see them all. Two here are hidden behind " },
  { file: "vo-09.mp3", at: beat("In the browser", 570), note: " Then it fetches every cited page and reads it." },
  { file: "vo-10.mp3", at: beat("In the browser", 735), note: " Every sentence comes back marked, with the source's own words underne" },
  { file: "vo-11.mp3", at: beat("What it does", 30), note: " It does not ask whether a claim is true." },
  { file: "vo-12.mp3", at: beat("What it does", 120), note: " It asks whether the page that was cited says it." },
  { file: "vo-13.mp3", at: beat("What it does", 234), note: " Supported means it quoted the page, and a script confirmed the quote " },
  { file: "vo-15.mp3", at: beat("The refusal", 78), note: " And sometimes it gives you nothing." },
  { file: "vo-16.mp3", at: beat("The refusal", 186), note: " This claim's only source is a page that is gone. There is nothing to " },
  { file: "vo-18.mp3", at: beat("The refusal", 378), note: " A number here is invented." },
  { file: "vo-19.mp3", at: beat("The refusal", 474), note: " It refuses at the answer level too." },
  { file: "vo-21.mp3", at: beat("Calibration", 102), note: " Forty five claims, labelled blind, before the judge saw any of them." },
  { file: "vo-22.mp3", at: beat("Calibration", 249), note: " Agreement is a kappa of 0.30, confidence interval 0.004 to 0.60, over" },
  { file: "vo-23.mp3", at: beat("Calibration", 480), note: " The lower bound is the honest part. Chance is not ruled out." },
  { file: "vo-24.mp3", at: beat("Calibration", 588), note: " It agrees best when the page simply does not say it. Worst when the p" },
  { file: "vo-25.mp3", at: beat("Close", 42), note: " It cannot tell you a source is right. A well cited falsehood passes." },
  { file: "vo-26.mp3", at: beat("Close", 165), note: " It can tell you when nobody checked." },
];
