// @flow
import React from 'react';
import type { Game, Bar } from '../../types';
import groupModelsByRound from './GroupModelsByRound';
import createCumulativeModels from './CreateCumulativeModels';
import createBarGroups from './CreateBarGroups';
import {
  createTipPointScale,
  createRoundScale,
  createColorScale,
} from './CreateScales';

import BarChart from '../../components/BarChart';
import Axis from '../../components/Axis';

type Props = {
  gamesByYear: Array<Game>
}

type State = {
  bars: Array<Array<Bar>>,
  xScale: Function,
  yScale: Function,
  isCalculating: boolean
}

const BAR_WIDTH = 4;
const WIDTH = 800;
const HEIGHT = 400;

class BarChartContainer extends React.Component<Props, State> {
  state = {
    bars: [],
    xScale: () => null,
    yScale: () => null,
    isCalculating: true,
  }

  componentDidMount() {
    const { gamesByYear } = this.props;
    this.setBars(gamesByYear);
  }

  componentDidUpdate(prevProps: { gamesByYear: Array<Game> }) {
    const { gamesByYear } = this.props;
    if (gamesByYear !== prevProps.gamesByYear) {
      this.setBars(gamesByYear);
    }
  }

  setBars(gamesByYear: Array<Game>) {
    const modelsByRound = groupModelsByRound(gamesByYear);
    const cumulativeModels = createCumulativeModels(modelsByRound);
    const xScale = createRoundScale(cumulativeModels, WIDTH);
    const yScale = createTipPointScale(cumulativeModels, HEIGHT);
    const colorScale = createColorScale();
    const bars = createBarGroups({
      barWidth: BAR_WIDTH,
      xScale,
      yScale,
      colorScale,
      cumulativeModels,
    });
    this.setState({
      bars,
      xScale,
      yScale,
      isCalculating: false,
    });
  }

  render() {
    const {
      bars,
      xScale,
      yScale,
      isCalculating,
    } = this.state;

    return (
      <div>
        {
          !isCalculating
          && (
            <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} style={{ height: 'auto', width: '100%' }}>
              <BarChart bars={bars} barWidth={BAR_WIDTH} />
              <Axis xScale={xScale} yScale={yScale} />
            </svg>
          )
        }
      </div>
    );
  }
}
export default BarChartContainer;
