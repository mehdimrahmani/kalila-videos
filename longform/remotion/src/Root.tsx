import React from 'react';
import {Composition, getInputProps} from 'remotion';
import {Longform} from './Longform';

// The episode is chosen at render time: --props='{"id":"lf01"}'. Duration comes from public/<id>/timeline.json.
const tls: Record<string, any> = {
  lf01: require('../public/lf01/timeline.json'),
};

export const Root: React.FC = () => {
  const {id = 'lf01'} = getInputProps() as {id?: string};
  const tl = tls[id] || tls.lf01;
  return (
    <Composition id="Longform" component={Longform} durationInFrames={Math.ceil(tl.duration * 30)} fps={30}
      width={1920} height={1080} defaultProps={{id: tl.id, timeline: tl}} />
  );
};
