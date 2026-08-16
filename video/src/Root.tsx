import "./index.css";
import { Composition, Folder, Still } from "remotion";
import { Film, FILM_DURATION, SCENES } from "./film/Film";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Film"
        component={Film}
        durationInFrames={FILM_DURATION}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* Each scene on its own, so a single moment can be previewed or restyled
          without scrubbing the whole cut. */}
      <Folder name="Scenes">
        {SCENES.map((scene) => (
          <Composition
            key={scene.name}
            id={scene.name.replace(/\s+/g, "")}
            component={scene.component}
            durationInFrames={scene.duration}
            fps={30}
            width={1920}
            height={1080}
          />
        ))}
      </Folder>

      <Folder name="Stills">
        <Still id="Poster" component={Film} width={1920} height={1080} />
      </Folder>
    </>
  );
};
