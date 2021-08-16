import dash
from dash.dependencies import Input, Output, State
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import pandas as pd
import json
import base64
import io


def name_and_df_from_json(json_text):
    print("Started json parcing")
    data = json.load(json_text)
    device_name = None
    data_for_df = {}
    datetimes = []
    for r in data:
        if data_for_df == {}:
            for sensor in data[r]['data']:
                try:
                    float(data[r]['data'][sensor])
                except ValueError as e:
                    continue
                else:
                    data_for_df[sensor] = []
            # device_name = "{} ({})".format(data[r]['uName'], data[r]['serial'])

        datetimes.append(pd.to_datetime(data[r]['Date']))
        for sensor in data[r]['data']:
            if sensor in data_for_df.keys():
                try:
                    data_for_df[sensor].append(float(data[r]['data'][sensor]))
                except ValueError:
                    data_for_df[sensor].append(None)

    df = pd.DataFrame(data_for_df, index=datetimes)
    return device_name, df


def parse_contests(contents, filename: str, date, av_param):
    if contents is not None and filename is not None and date is not None:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        print("File downloaded")
        if '.csv' in filename:
            csv_text = io.StringIO(decoded.decode("windows-1251"))
            device_name = csv_text.readline().split(';')[1]
            df = pd.read_csv(csv_text, sep=';')
            try:
                df = df.drop('Unnamed: 15', axis=1)
            except KeyError:
                pass
            df = df.set_index('Date')
            df.index = pd.to_datetime(df.index)

        elif '.json' in filename:
            device_name, df = name_and_df_from_json(io.StringIO(decoded.decode("utf-8")))
        else:
            return html.Div([
                "Only csv or json files are readable"
            ])
        if av_param != 'None':
            if av_param != 'max' and av_param != 'min':
                df = df.resample(av_param).mean()
            elif av_param == 'max':
                df = df.resample('1d').max()
            elif av_param == 'min':
                df = df.resample('1d').min()
        device_name = filename
        return html.Div([
            html.H3(f'Read from file "{filename}" / Data for device "{device_name}"'),
            dcc.Graph(
                id='file-graph',
                figure={
                    'data': [go.Scatter(x=list(df.index), y=list(df[sens]), name=sens, mode='lines') for sens in df.keys()],
                    'layout': {
                        'xaxis': {'title': filename.removesuffix('.json') }
                        }
                },
                # relayoutData={'yaxis': {'title': 'y'}},
            )
        ])
    else:
        return html.Div()


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    # html.H1(children='Build using Dash and Pandas'),
    html.Div(id='file-chart'),
    dcc.RadioItems(id='opt',
                   options=[
                       {'label': 'Without average', 'value': 'None'},
                       {'label': 'Average for every 1H', 'value': '1H'},
                       {'label': 'Average for every 3H', 'value': '3H'},
                       {'label': 'Average for every 24H', 'value': '1d'},
                       {'label': 'Max for every 24H', 'value': 'max'},
                       {'label': 'Min for every 24H', 'value': 'min'},
                   ],
                   value='None'
                   ),
    dcc.Upload(
        id='upload',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
])


@app.callback(Output('file-chart', 'children'), [Input('upload', 'contents'), Input('opt', 'value')],
              [State('upload', 'filename'), State('upload', 'last_modified')])
def file_chart_update(list_of_contents, av_param, list_of_names, list_of_dates):
    return [parse_contests(list_of_contents, list_of_names, list_of_dates, av_param)]


if __name__ == '__main__':
    app.run_server(debug=True)
