import { loadFont as loadJetBrainsMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadRethinkSans } from "@remotion/google-fonts/RethinkSans";

// Rethink Sans carries both the display and the body type. JetBrains Mono stays
// for anything quoting machine output, because a verdict label and a gate code
// should not look like they were written by a person.
loadRethinkSans();
loadJetBrainsMono();
