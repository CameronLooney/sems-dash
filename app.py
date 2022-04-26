import streamlit as st
import pandas as pd
import numpy as np
import itertools
import plotly.express as px

from natsort import natsort_keygen
import os
import time

st.set_page_config(page_title = 'SEMs Dashboard',layout='wide',page_icon=':bar_chart')

### top row
st.sidebar.markdown("## Dashboard Parameters")
path = os.path.join(os.path.expanduser("~"), "Library/CloudStorage/Box-Box/SEMS data for Dashboard/")



def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():

    sems = st.sidebar.file_uploader("Upload SEMS data", type="xlsx")
    if sems is not None:


        @st.experimental_memo
        def read_excel(df):
            sems_df = pd.read_excel(df, sheet_name=0, engine="openpyxl")
            return sems_df
        sems_df = read_excel(sems)


        @st.experimental_memo
        def data_filter(df):
            # 1. Drop unneeded columns
            # 2. Drop non Western Europe
            # 3. Drop RMA -> Failed Pickup etc
            # 4. Drop AOU
            # is Telco needed??
            cols_to_drop = ['RMA  Nr', 'Assigned To User Name', 'Resolution', 'Wk 12/13', 'Sales District']
            df.drop(cols_to_drop, inplace=True, axis=1)
            regions_to_keep = ['South Europe', "DACH", 'UK&I', 'North Europe']
            df = df[df["Sales Region"].isin(regions_to_keep)]
            df = df[~df["Created by Team Name"].str.contains("RMA")]
            df = df[~df["Created by Team Name"].str.contains("CSS CRU")]
            df = df[~df["Carrier"].str.contains("RMA",na=False)]
            df = df[~df["CAT"].str.contains("AOU")]

            return df


        sems_df = data_filter(sems_df)


        with st.sidebar.form(key='my_form_to_submit'):

            with st.sidebar:
                from datetime import date,timedelta
                def start_data_date():
                    start_date = st.date_input('Start Date', value=(date.today() - timedelta(30)))
                    start_date = str(start_date)
                    return start_date
                start_date = start_data_date()
                def end_data_date():
                    end = st.date_input('End Date', value=date.today())
                    end_date = str(end)
                    return end_date
                end_date = end_data_date()






                sems_df["Created On"] = sems_df["Created On"].astype(str)
                sems_df = sems_df[(sems_df["Created On"] >= start_date) & (sems_df["Created On"] <=end_date)]
                print("DATE RANGE ")
                print(len(sems_df.index))
                def dashboard_section_selector():
                    dashb_part = st.multiselect(
                        "Pick which Dashboards to See",
                        ["Main KPI's", 'Open SEMS', 'Carrier', 'Customer','Region', "Category", "Additional Analysis"],
                        ["Main KPI's"])
                    return dashb_part
                dashboard_selection = dashboard_section_selector()
                @st.experimental_memo
                def sort_quarters(df):
                    year_quarter_list = df["FW"].unique()
                    year_quarter_list = [i.split('W', 1)[0] for i in year_quarter_list]
                    quarter_list = []
                    for i in year_quarter_list:
                        if i not in quarter_list:
                            quarter_list.append(i)

                    fq_params = sorted(quarter_list,reverse=True)
                    return fq_params
                fq_params = sort_quarters(sems_df)
                def number_of_weeks(df):
                    return len(list(df['FW'].unique()))
                number_of_weeks_in_data = number_of_weeks(sems_df)
                submit_button = st.form_submit_button(label='Update Dashboard Parameters')



        if st.sidebar.button("Generate Dashboard"):
            # zip two lists and drop all rows not in and boom we are done

            @st.experimental_memo
            def drop_unneeded_date_row(df,start,end):
                sems_df = df[(df["Created On"] >= start) & (df["Created On"] <= end)]
                return sems_df

            graph_data = drop_unneeded_date_row(sems_df,start_date,end_date)
            if len(graph_data["FW"].unique())==0:
                st.error("ERROR: No SEMS Data to Analyse")


            @st.experimental_memo
            def add_quarters_column(df):
                df['Quarter'] = (np.where(df['FW'].str.contains('W'),
                                       df['FW'].str.split('W').str[0],
                                       df['FW']))
                return df
            graph_data = add_quarters_column(graph_data)


            #quarter_list= sems_df['FW'].str.split('W', 1, expand=True).unqiue()
            @st.experimental_memo
            def open_status_df(df):
                status = ["Open"]
                df = df[df["SEM Status"].isin(status)]
                return df


            @st.experimental_memo
            def closed_status_df(df):
                status = ["Closed"]
                df = df[df["SEM Status"].isin(status)]
                return df
            st.markdown("# SEMS DASHBOARD")

            st.markdown("<hr/>", unsafe_allow_html=True)


            def percentage(part, whole):
                if round(float(whole), 0) == 0:
                    return str(round(100 * float(part), 2))
                Percentage = round(100 * float(part) / float(whole), 2)
                return str(Percentage) + '%'


            def row_count(df):
                num_rows = len(df.index)
                return num_rows


            def open_closed_status_df(df):
                status = ["Open", "Closed"]
                df = df[df["SEM Status"].isin(status)]
                return df
            def value_counts_df(df, col):

                df = df.groupby(col).size()
                df = pd.DataFrame(df, columns=['Count'])
                df.index.name = col
                df[col] = df.index
                return df


            def df_with_two(df, col):
                values = sorted(list(df[col].unique()), reverse=True)
                values = values[:2]
                df_compare = df[df[col].isin(values)]
                return df_compare


            def current_df(df, col):
                values = sorted(list(df[col].unique()), reverse=True)
                df_compare = df[df[col] == values[0]]
                return df_compare


            def previous_df(df, col):
                values = sorted(list(df[col].unique()), reverse=True)
                df_compare = df[df[col] == values[1]]
                return df_compare



            if "Main KPI's" in dashboard_selection:

                st.markdown("## Main KPIs")

                first_kpi, second_kpi, third_kpi = st.columns(3)




                with first_kpi:
                    st.markdown("**Number of SEMS**")
                    num_sems = len(graph_data.index)
                    st.markdown(f"<h1 style='text-align: left; color: gold;'>{num_sems}</h1>", unsafe_allow_html=True)
                with second_kpi:
                    st.markdown("**Number of Open Cases**")
                    num_open = graph_data['SEM Status'].str.contains(r"Open").sum()
                    st.markdown(f"<h1 style='text-align: left; color: gold;'>{num_open}</h1>", unsafe_allow_html=True)
                with third_kpi:
                    st.markdown("**No. Open Priority 1**")
                    open_df = open_status_df(graph_data)
                    num_p1 = open_df['Priority'].str.contains(r"P1").sum()

                    st.markdown(f"<h1 style='text-align: left; color: gold;'>{num_p1}</h1>",
                                unsafe_allow_html=True)





                ### second row

                st.markdown("<hr/>", unsafe_allow_html=True)

                st.markdown("## Secondary KPIs")






                first_kpi, second_kpi, third_kpi, fourth_kpi, fifth_kpi = st.columns(5)
                with first_kpi:
                    st.markdown("**% of Cases Open**")
                    open_status_count  = graph_data['SEM Status'].str.contains(r"Open").sum()
                    open_percent = percentage(open_status_count,row_count(graph_data))
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{open_percent}</h1>", unsafe_allow_html=True)

                with second_kpi:
                    st.markdown("**Team Most Cases**")
                    open_df = open_status_df(graph_data)
                    x = open_df.groupby('Assigned To Team').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Team"] = df.index
                    df = df.sort_values('Count')
                    team_name = (df['Team'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 15px;'>{team_name}</h1>",unsafe_allow_html=True)

                with third_kpi:
                    st.markdown("**Most Common Issue**")
                    open_df = open_status_df(graph_data)
                    x = open_df.groupby('SEM Issue Type').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Issue"] = df.index
                    df = df.sort_values('Count')
                    issue_name = (df['Issue'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 15px;'>{issue_name}</h1>", unsafe_allow_html=True)

                with fourth_kpi:
                    st.markdown("**% of Open Priority 1**")
                    open_df = open_status_df(graph_data)
                    num_p1 = open_df['Priority'].str.contains(r"P1").sum()

                    percent_p1 = percentage(num_p1, row_count(open_df))
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{percent_p1}</h1>",unsafe_allow_html=True)

                with fifth_kpi:
                    st.markdown("**N. of Priority 1**")
                    num_p1 = graph_data['Priority'].str.contains(r"P1").sum()
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 30px;'>{num_p1}</h1>", unsafe_allow_html=True)
                st.markdown("<hr/>", unsafe_allow_html=True)
                if len(graph_data["FW"].unique())>=2:
                    st.markdown("## Week on Week Markers")


                    weeks_to_compare = df_with_two(graph_data,"FW")
                    df_weeks = value_counts_df(weeks_to_compare,'FW')

                    first_weekly_marker, second_weekly_marker,third_weekly_marker, fourth_weekly_marker,fifth_weekly_marker= st.columns(5)
                    def num_sems_weekly_marker():
                        df = value_counts_df(weeks_to_compare, 'FW')
                        with first_weekly_marker:
                            percent_diff = percentage((int(df['Count'].iloc[1])-int(df['Count'].iloc[0])),df['Count'].iloc[0])
                            st.metric(label="No. SEMS",value=df['Count'].iloc[1], delta=percent_diff,delta_color = "inverse")

                    num_sems_weekly_marker()

                    def num_sems_open_weekly_marker():
                        current_week = current_df(graph_data,"FW")
                        current_week = current_week['SEM Status'].str.contains(r"Open").sum()
                        previous_week = previous_df(graph_data,"FW")
                        previous_week = previous_week['SEM Status'].str.contains(r"Open").sum()

                        with second_weekly_marker:
                            percent_diff = percentage((int(current_week)-int(previous_week)),previous_week)
                            st.metric(label="No. Open SEMS",value=current_week, delta=percent_diff,delta_color = "inverse")

                    num_sems_open_weekly_marker()


                    def num_sems_open_percent_weekly_marker():
                        current_week = current_df(graph_data,"FW")
                        current_week_open = current_week['SEM Status'].str.contains(r"Open").sum()
                        previous_week = previous_df(graph_data,"FW")
                        previous_week_open = previous_week['SEM Status'].str.contains(r"Open").sum()
                        current_percent = percentage(current_week_open, row_count(current_week))
                        previous_percent = percentage(previous_week_open, row_count(previous_week))
                        current_percent_int = float(str(current_percent).replace("%", ""))
                        previous_percent_int = float(str(previous_percent).replace("%", ""))
                        print("current_percent" + str(current_percent))
                        print("previous_percent" + str(previous_percent))


                        with third_weekly_marker:
                            percent_diff = str(round(current_percent_int - previous_percent_int,2))+"%"
                            st.metric(label="% Open SEMS",value=current_percent, delta=percent_diff,delta_color = "inverse")

                    num_sems_open_percent_weekly_marker()

                    def num_priority1_weekly_marker():
                        current_week = current_df(graph_data,"FW")
                        current_week = current_week['Priority'].str.contains(r"P1").sum()
                        previous_week = previous_df(graph_data,"FW")
                        previous_week = previous_week['Priority'].str.contains(r"P1").sum()
                        print("previous prioity1 " + str(previous_week))

                        with fourth_weekly_marker:
                            percent_diff = percentage((int(current_week)-int(previous_week)),previous_week)
                            st.metric(label="No. Priority 1",value=current_week, delta=percent_diff,delta_color = "inverse")


                    num_priority1_weekly_marker()

                    def num_priority1_open_weekly_marker():
                        current_week = current_df(graph_data,"FW")
                        current_week  = current_week[current_week["SEM Status"] == "Open"]
                        current_week = current_week['Priority'].str.contains(r"P1").sum()
                        previous_week = previous_df(graph_data,"FW")
                        previous_week = previous_week[previous_week["SEM Status"] == "Open"]
                        previous_week = previous_week['Priority'].str.contains(r"P1").sum()

                        with fifth_weekly_marker:
                            percent_diff = percentage((int(current_week)-int(previous_week)),previous_week)
                            st.metric(label="No. Open Priority 1",value=current_week, delta=percent_diff,delta_color = "inverse")


                    num_priority1_open_weekly_marker()







                    st.markdown("<hr/>", unsafe_allow_html=True)



                if len(fq_params) >= 2:
                    st.markdown("## Quarter on Quarter Markers")
                    first_quarterly_marker, second_quarterly_marker, third_quarterly_marker = st.columns(3)



                    quarters_to_compare = df_with_two(graph_data,"Quarter")

                    def num_sems_quarterly_marker():
                        df = value_counts_df(quarters_to_compare, 'Quarter')
                        with first_quarterly_marker:
                            percent_diff = percentage((int(df['Count'].iloc[1]) - int(df['Count'].iloc[0])),
                                                      df['Count'].iloc[0])
                            st.metric(label="No. SEMS", value=df['Count'].iloc[1], delta=percent_diff, delta_color="inverse")


                    num_sems_quarterly_marker()
                    def num_priority1_quarterly_marker():
                        current_quarter = current_df(graph_data,"Quarter")
                        current_quarter = current_quarter['Priority'].str.contains(r"P1").sum()
                        previous_quarter = previous_df(graph_data,"Quarter")
                        previous_quarter = previous_quarter['Priority'].str.contains(r"P1").sum()


                        with second_quarterly_marker:
                            percent_diff = percentage((int(current_quarter)-int(previous_quarter)),previous_quarter)
                            st.metric(label="No. Priority 1",value=current_quarter, delta=percent_diff,delta_color = "inverse")


                    num_priority1_quarterly_marker()
                    def percent_p1_quarterly_marker():
                        current_quarter = current_df(graph_data, "Quarter")
                        current_quarter_sum = current_quarter['Priority'].str.contains(r"P1").sum()
                        previous_quarter = previous_df(graph_data, "Quarter")
                        previous_quarter_sum = previous_quarter['Priority'].str.contains(r"P1").sum()
                        current_percent = percentage(current_quarter_sum, row_count(current_quarter))
                        previous_percent = percentage(previous_quarter_sum, row_count(previous_quarter))
                        current_percent_int = float(str(current_percent).replace("%", ""))
                        previous_percent_int = float(str(previous_percent).replace("%", ""))
                        print("current_percent_int" + str(current_percent_int))
                        print("previous_percent_int" + str(previous_percent_int))


                        with third_quarterly_marker:
                            percent_diff = str(round(current_percent_int - previous_percent_int,2))+"%"
                            st.metric(label="% Priority 1",value=current_percent, delta=percent_diff,delta_color = "inverse")


                    percent_p1_quarterly_marker()
                st.markdown("<hr/>", unsafe_allow_html=True)





           # --------------------------------- WEEK ON WEEK MARKERS -----------------------------------






            if "Open SEMS" in dashboard_selection:

                st.markdown("## Open SEM Status")

                first_chart, second_chart = st.columns(2)

                def plot_hist_sem_status():
                    with first_chart:
                        fig = px.histogram(data_frame=graph_data, x='SEM Status', title='Histogram of SEM Status',color_discrete_sequence = ['gold'],text_auto=True).update_xaxes(categoryorder='total descending')
                        st.plotly_chart(fig, use_container_width=True)
                plot_hist_sem_status()

                def hist_open_region():
                    with second_chart:
                        df = open_status_df(graph_data)
                        fig = px.histogram(data_frame=df, x='Sales Region', title='Histogram of Open SEMS by Region',color_discrete_sequence = ['gold'],text_auto=True).update_xaxes(
                            categoryorder='total descending')
                        st.plotly_chart(fig, use_container_width=True)
                hist_open_region()
                first_chart_row2, second_chart_row2 = st.columns([3,6])

                def hist_cat_open_frequency():
                    with first_chart_row2:
                        df_open = open_status_df(graph_data)
                        fig = px.histogram(data_frame=df_open, x='CAT', title='Histogram of CAT Frequency', text_auto=True,
                                           color='CAT',
                                           color_discrete_map={'RO': 'gold',
                                                               'AOU': '#c552e4',
                                                               'TEL': '#00d1ff'
                                                               }
                                           )

                        st.plotly_chart(fig, use_container_width=True)
                hist_cat_open_frequency()

                def hist_top10_partners_open():
                    with second_chart_row2:
                        df_open = open_status_df(graph_data)
                        x = df_open.groupby('Sold-To ID').size()
                        df = pd.DataFrame(x, columns=['Count'])
                        df["Sold-To ID"] = df.index
                        df = df.sort_values('Count', ascending=[False])
                        df = df.head(n=10)
                        fig = px.histogram(data_frame=df, x='Sold-To ID', y="Count", title = "Top 10 Partners by Open Orders",color_discrete_sequence=['gold'],
                                           text_auto=True)
                        st.plotly_chart(fig, use_container_width=True)
                hist_top10_partners_open()



                def hist_top10_open_team():
                    df_open = open_status_df(graph_data)
                    x = df_open.groupby('Assigned To Team').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df['Assigned To Team'] = df.index
                    df = df.sort_values('Count', ascending=[False])
                    df = df.head(n=10)
                    fig = px.histogram(data_frame=df, x='Assigned To Team', y="Count", title="Top 10 Teams by Open Orders",
                                       color_discrete_sequence=['gold'],
                                       text_auto=True)

                    st.plotly_chart(fig, use_container_width=True)
                hist_top10_open_team()
                def hist_top10_open_issue():
                    df_open = open_status_df(graph_data)
                    x = df_open.groupby('SEM Issue Type').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df['SEM Issue Type'] = df.index
                    df = df.sort_values('Count', ascending=[False])
                    df = df.head(n=10)
                    fig = px.histogram(data_frame=df, x='SEM Issue Type', y="Count", title="Top 10 Issues by Open Orders",
                                       color_discrete_sequence=['gold'],
                                       text_auto=True)

                    st.plotly_chart(fig, use_container_width=True)
                hist_top10_open_issue()
                if len(graph_data["FW"].unique())>=3:

                    def open_order_trend():
                        x = graph_data.groupby(["FW"]).size().reset_index(name="Count")
                        fig = px.scatter(data_frame=x, x="FW", y="Count", title='Open SEM Trend',
                                         color_discrete_sequence=['gold'])
                        fig.update_layout(xaxis=dict(showgrid=False),
                                          yaxis=dict(showgrid=False)
                                          )
                        fig.update_traces(mode='lines')
                        st.plotly_chart(fig, use_container_width=True)
                    open_order_trend()

                if len(graph_data["FW"].unique()) >= 2:
                    status = ["Open", "Closed"]
                    df = graph_data[graph_data["SEM Status"].isin(status)]
                    from natsort import natsort_keygen
                    df = df.sort_values(by="FW",key=natsort_keygen())

                    fig = px.histogram(data_frame=df, x='FW', title='SEM Status Weekly',
                                       color = "SEM Status",text_auto=True,
                                       color_discrete_map={'Open': 'gold',
                                                           'Closed': '#00d1ff',
                                                           }
                                       )
                    fig.update_layout(barmode='group')




                    st.plotly_chart(fig, use_container_width=True)
                    fig.update_layout(xaxis=dict(showgrid=False),
                                      yaxis=dict(showgrid=True)
                                      )
                st.markdown("### Open SEM Summary")
                first_open, second_open, third_open, fourth_open = st.columns(4)
                with first_open:
                    st.markdown("**Team Most Open Cases**")
                    open_df = open_status_df(graph_data)
                    x = open_df.groupby('Assigned To Team').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Team"] = df.index
                    df = df.sort_values('Count')
                    team_name = (df['Team'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 20px;'>{team_name}</h1>",
                                unsafe_allow_html=True)
                with second_open:
                    st.markdown("**Region Most Open Cases**")
                    x = open_df.groupby('Sales Region').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Sales Region"] = df.index
                    df = df.sort_values('Count')
                    region_name = (df['Sales Region'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 20px;'>{region_name}</h1>",
                                unsafe_allow_html=True)
                with third_open:
                    st.markdown("**CAT Most Open Cases**")
                    x = open_df.groupby('CAT').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df['CAT'] = df.index
                    df = df.sort_values('Count')
                    region_name = (df['CAT'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 20px;'>{region_name}</h1>",
                                unsafe_allow_html=True)
                with fourth_open:
                    st.markdown("**Partner Most Open Cases**")
                    x = open_df.groupby('Sold-To ID').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df['Sold-To ID'] = df.index
                    df = df.sort_values('Count')
                    region_name = (df['Sold-To ID'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 20px;'>{region_name}</h1>",
                                unsafe_allow_html=True)




                st.markdown("----", unsafe_allow_html=True)
            if "Priority" in dashboard_selection:
                st.markdown("## Priority")

                priority_column1, priority_column2 = st.columns(2)

                df = graph_data.sort_values(by="FW", key=natsort_keygen())

                fig = px.histogram(data_frame=df, x='FW', title='Priority 1 vs 2 Weekly',
                                       color="Priority",text_auto=True,
                                   color_discrete_map={'P1': 'gold',
                                                       'P2': '#00d1ff',
                                                       }
                                   )
                fig.update_layout(barmode='group')

                st.plotly_chart(fig, use_container_width=True)


                open = open_status_df(graph_data)
                df = open.sort_values(by="FW", key=natsort_keygen())

                fig = px.histogram(data_frame=df, x='FW', title='Priority 1 vs 2 Weekly Open',
                                       color="Priority",text_auto=True,
                                   color_discrete_map={'P1': 'gold',
                                                       'P2': '#00d1ff',
                                                      }
                )
                fig.update_layout(barmode='group')

                st.plotly_chart(fig, use_container_width=True)


                open = open_status_df(graph_data)
                x = open.groupby(['Sales Region','Priority']).size()
                new_df = x.to_frame(name='Count').reset_index()
                new_df = new_df.sort_values('Count', ascending=[False])
                fig = px.histogram(data_frame=new_df, x='Sales Region',y="Count", title='Open P1 vs P2 by Region',
                                   color="Priority", text_auto=True,
                                   color_discrete_map={'P1': 'gold',
                                                       'P2': '#00d1ff',
                                                       }
                                   )
                fig.update_layout(barmode='group')

                st.plotly_chart(fig, use_container_width=True)
                first_priority, second_priority = st.columns(2)
                with first_priority:
                    open = open_status_df(graph_data)
                    x = open.groupby(['CAT', 'Priority']).size()
                    new_df = x.to_frame(name='Count').reset_index()
                    new_df = new_df.sort_values('Count', ascending=[False])
                    fig = px.histogram(data_frame=new_df, x='CAT', y="Count", title='Open P1 vs P2 by CAT',
                                       color="Priority", text_auto=True,
                                       color_discrete_map={'P1': 'gold',
                                                           'P2': '#00d1ff',
                                                           }
                                       )
                    fig.update_layout(barmode='group')

                    st.plotly_chart(fig, use_container_width=True)
                with second_priority:
                    open = open_status_df(graph_data)
                    fig = px.histogram(data_frame=open, x='Priority', title='Total Open P1 vs P2',
                                       color="Priority", text_auto=True,
                                       color_discrete_map={'P1': 'gold',
                                                           'P2': '#00d1ff',
                                                           }
                                       )
                    fig.update_layout(barmode='group')

                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Priority Summary")
                first_priority, second_priority, third_priority, fourth_priority, fifth_priority = st.columns(5)
                open_dataframe = open_status_df(graph_data)
                with first_priority:
                    st.markdown("**No. Open Priority 1**")
                    num_p1 = open_dataframe['Priority'].str.contains(r"P1").sum()

                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{num_p1}</h1>",
                                unsafe_allow_html=True)


                with second_priority:
                    st.markdown("**No. Open Priority 2**")
                    num_p2 = open_dataframe['Priority'].str.contains(r"P2").sum()

                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{num_p2}</h1>",
                                unsafe_allow_html=True)

                with third_priority:
                    st.markdown("**% of Open Priority 1**")
                    open_df = open_status_df(graph_data)
                    num_p1 = open_df['Priority'].str.contains(r"P1").sum()

                    percent_p1 = percentage(num_p1, row_count(open_df))
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{percent_p1}</h1>",
                                unsafe_allow_html=True)


                with fourth_priority:
                    st.markdown("**% of Open Priority 2**")
                    open_df = open_status_df(graph_data)
                    num_p2 = open_df['Priority'].str.contains(r"P2").sum()

                    percent_p2 = percentage(num_p2, row_count(open_df))
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{percent_p2}</h1>",
                                unsafe_allow_html=True)
                with fifth_priority:
                    st.markdown("**No. of P1 Total**")
                    num_p1 = graph_data['Priority'].str.contains(r"P1").sum()
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 30px;'>{num_p1}</h1>",
                                unsafe_allow_html=True)
                st.markdown("<hr/>", unsafe_allow_html=True)

            if "Category" in dashboard_selection:
                st.markdown("## Category Analysis (RO/TEL/AOU)")




                first_chart, second_chart = st.columns(2)


                with first_chart:
                    fig =px.histogram(data_frame=graph_data, x='CAT',title ='Histogram of CAT Frequency',text_auto=True,color = 'CAT',
                                      color_discrete_map={'RO': 'gold',
                                                          'AOU': '#c552e4',
                                                          'TEL': '#00d1ff'
                                                          }
                                      )
                    st.plotly_chart(fig,use_container_width=True)




                with second_chart:
                    fig = px.pie(graph_data, values='SEM ID', names='CAT',title ='PieChart of CAT Frequency', hole = 0.6,color = 'CAT',color_discrete_map={'RO': 'gold',
                                                          'AOU': '#c552e4',
                                                          'TEL': '#00d1ff'
                                                          })
                    st.plotly_chart(fig, use_container_width=True)


                if len(graph_data["FW"].unique())>2:
                    x = graph_data.groupby(["FW", "CAT"]).size().reset_index(name="Count")
                    fig = px.scatter(data_frame=x, x="FW", y="Count", color='CAT',title = 'Total No. SEM Trend',color_discrete_map={'RO': 'gold',
                                                          'AOU': '#c552e4',
                                                          'TEL': '#00d1ff'
                                                          })
                    fig.update_layout(xaxis=dict(showgrid=False),
                                      yaxis=dict(showgrid=False)
                                      )
                    fig.update_traces(mode='lines')
                    st.plotly_chart(fig, use_container_width=True)

                    x = graph_data.loc[graph_data['SEM Status'] == "Open"]
                    # stops the graph going mental and misconnecting
                    x = x.groupby(["FW", "CAT"]).size().unstack(fill_value=0).stack().reset_index(name="Count")

                    fig = px.line(data_frame=x, x="FW", y="Count", color='CAT', title='Open SEM Trend',color_discrete_map={'RO': 'gold',
                                                          'AOU': '#c552e4',
                                                          'TEL': '#00d1ff'
                                                          })
                    fig.update_layout(xaxis=dict(showgrid=False),
                                      yaxis=dict(showgrid=False)
                                      )
                    #fig.update_traces(mode='lines')
                    st.plotly_chart(fig, use_container_width=True)

                    st.markdown("### CAT Summary")
                first_cat, second_cat, third_cat, fourth_cat, fifth_cat = st.columns(5)
                open_dataframe = open_status_df(graph_data)
                with first_cat:
                    st.markdown("**Largest CAT**")
                    largest = graph_data
                    x = largest.groupby('CAT').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["CAT"] = df.index
                    df = df.sort_values('Count')
                    print(df['Count'].values[-1])
                    team_name = (df['CAT'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{team_name}</h1>",
                                unsafe_allow_html=True)


                with second_cat:
                    st.markdown("**% of Total**")
                    largest_sum = df['Count'].values[-1]
                    total = df["Count"].sum()
                    percent = percentage(largest_sum,total)


                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{percent}</h1>",
                                unsafe_allow_html=True)

                with third_cat:
                    st.markdown("**Total No. SEMS**")
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{df['Count'].values[-1]}</h1>",
                                unsafe_allow_html=True)

                with fourth_cat:
                    st.markdown("**No. Open SEMS**")
                    open_df = open_status_df(graph_data)
                    x = open_df.groupby('CAT').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["CAT"] = df.index
                    df = df.sort_values('Count')


                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{df['Count'].values[-1]}</h1>",
                                unsafe_allow_html=True)
                with fifth_cat:
                    st.markdown("**No. of Open P1**")
                    open_p1 = open_df[open_df["CAT"] == team_name]
                    num_p1 = open_p1['Priority'].str.contains(r"P1").sum()
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 30px;'>{num_p1}</h1>",
                                unsafe_allow_html=True)
                st.markdown("<hr/>", unsafe_allow_html=True)









                # top 10 partners

            if "Partner" in dashboard_selection:
                st.markdown("## Top Partner Analysis")
                x = graph_data.groupby('Sold-To ID').size()
                df_partner = pd.DataFrame(x, columns=['Count'])
                df_partner["Sold-To ID"] = df_partner.index
                df_partner = df_partner.sort_values('Count',ascending=[False])
                df_partner = df_partner.head(n=10)


                fig = px.histogram(data_frame=df_partner,title = "SEMS per Top 10 Partners",x='Sold-To ID',y="Count",color_discrete_sequence=['gold'],text_auto=True)

                st.plotly_chart(fig, use_container_width=True)

                open_df = open_status_df(graph_data)
                x = open_df.groupby('Sold-To ID').size()
                df = pd.DataFrame(x, columns=['Count'])
                df["Sold-To ID"] = df.index
                df = df.sort_values('Count', ascending=[False])
                df = df.head(n=10)
                fig = px.histogram(data_frame=df, title="Open SEMS by Partner", x='Sold-To ID', y="Count", color_discrete_sequence=['gold'],
                                   text_auto=True)

                st.plotly_chart(fig, use_container_width=True)

                top_10_partners = list(df["Sold-To ID"])
                x = graph_data.groupby(['Sold-To ID', 'Priority']).size()
                new_df = x.to_frame(name='Count').reset_index()
                new_df = new_df.sort_values('Count', ascending=[False])
                new_df = new_df[new_df["Sold-To ID"].isin(top_10_partners)]
                fig = px.histogram(data_frame=new_df, x='Sold-To ID', y="Count", title='P1 vs P2 by Partner',
                                   color="Priority", text_auto=True,
                                   color_discrete_map={'P1': 'gold',
                                                       'P2': '#00d1ff',
                                                       }
                                   )
                fig.update_layout(barmode='group')

                st.plotly_chart(fig, use_container_width=True)

                top_10_partners = list(df["Sold-To ID"])
                open = open_status_df(graph_data)
                x = open.groupby(['Sold-To ID', 'Priority']).size()
                new_df = x.to_frame(name='Count').reset_index()
                new_df = new_df.sort_values('Count', ascending=[False])
                new_df = new_df[new_df["Sold-To ID"].isin(top_10_partners)]
                fig = px.histogram(data_frame=new_df, x='Sold-To ID', y="Count", title='P1 vs P2 Open SEMS by Partner',
                                   color="Priority", text_auto=True,
                                   color_discrete_map={'P1': 'gold',
                                                       'P2': '#00d1ff',
                                                       }
                                   )
                fig.update_layout(barmode='group')

                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Top 10 Partners Summary")
                first_partner, second_partner,third_partner ,fourth_partner,fifth_partner = st.columns(5)

                with first_partner:
                    st.markdown("**Number of SEMS**")
                    num_sems = df_partner['Count'].sum()
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 30px;'>{num_sems}</h1>", unsafe_allow_html=True)
                with second_partner:
                    st.markdown("**No Open SEMS**")
                    num_sems_open = new_df['Count'].sum()
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 30px;'>{num_sems_open}</h1>", unsafe_allow_html=True)

                with third_partner:
                    st.markdown("**Percent of Total**")
                    sem_percent = percentage(num_sems,row_count(graph_data))
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 30px;'>{sem_percent}</h1>", unsafe_allow_html=True)
                with fourth_partner:
                    st.markdown("**Percent Open**")
                    num_open_sems = new_df['Count'].sum()
                    sems_percent_open = percentage(num_open_sems,num_sems)
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 30px;'>{sems_percent_open}</h1>", unsafe_allow_html=True)
                with fifth_partner:
                    st.markdown("**Largest Partner**")
                    largest = df_partner["Sold-To ID"].iloc[0]
                    st.markdown(f"<h1 style='text-align: left; color: gold;font-size: 20px;'>{largest}</h1>", unsafe_allow_html=True)

                st.markdown("<hr/>", unsafe_allow_html=True)

                ## REGION
            if "Region" in dashboard_selection:
                st.markdown("## Region Analysis")
                x = graph_data.groupby('Sales Region').size()
                df_region = pd.DataFrame(x, columns=['Count'])
                df_region['Sales Region'] = df_region.index
                df_region = df_region.sort_values('Count', ascending=[False])


                fig = px.histogram(data_frame=df_region, title="Total SEMS by Region", x='Sales Region', y="Count",
                                   color_discrete_sequence=['gold'], text_auto=True)

                st.plotly_chart(fig, use_container_width=True)


                x = open.groupby(['Sales Region', 'Priority']).size()
                new_df = x.to_frame(name='Count').reset_index()
                new_df = new_df.sort_values('Count', ascending=[False])
                fig = px.histogram(data_frame=new_df, x='Sales Region', y="Count", title='P1 vs P2 Open SEMS by Partner',
                                   color="Priority", text_auto=True,
                                   color_discrete_map={'P1': 'gold',
                                                       'P2': '#00d1ff',
                                                       }
                                   )
                fig.update_layout(barmode='group')

                st.plotly_chart(fig, use_container_width=True)

                x = graph_data.groupby(['Sales Region', 'CAT']).size()
                new_df = x.to_frame(name='Count').reset_index()
                new_df = new_df.sort_values('Count', ascending=[False])
                fig = px.histogram(data_frame=new_df, x='Sales Region', y="Count", title='Total SEMS per CAT Breakdown by Region',
                                   color="CAT", text_auto=True,
                                   color_discrete_map={'RO': 'gold',
                                                       'AOU': '#c552e4',
                                                       'TEL': '#00d1ff'
                                                       }
                                   )

                fig.update_layout(barmode='group')

                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Region Summary")
                first_region,second_region, third_region , fourth_region= st.columns(4)
                with first_region:
                    st.markdown("**Region Most SEMS**")

                    x = graph_data.groupby('Sales Region').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Region"] = df.index
                    df = df.sort_values('Count')
                    region_name = (df['Region'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{region_name}</h1>",
                                unsafe_allow_html=True)
                with second_region:
                    st.markdown("**No. SEMS**")
                    x = graph_data.groupby('Sales Region').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Region"] = df.index
                    df = df.sort_values('Count')
                    count_total = (df['Count'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{count_total}</h1>",
                                unsafe_allow_html=True)
                with third_region:
                    st.markdown("**No. Open SEMS**")
                    open = open_status_df(graph_data)
                    x = open.groupby('Sales Region').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Region"] = df.index
                    df = df.sort_values('Count')
                    count_total_open = (df['Count'].values[-1])
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{count_total_open}</h1>",
                                unsafe_allow_html=True)
                with fourth_region:
                    st.markdown("**Percent Open**")
                    open = open_status_df(graph_data)
                    x = open.groupby('Sales Region').size()
                    df = pd.DataFrame(x, columns=['Count'])
                    df["Region"] = df.index
                    df = df.sort_values('Count')
                    percent_open_region = percentage(count_total_open,count_total)
                    st.markdown(f"<h1 style='text-align: left; color: gold; font-size: 30px;'>{percent_open_region}</h1>",
                                unsafe_allow_html=True)

                st.markdown("<hr/>", unsafe_allow_html=True)
                # Additional Analysis
            if "Additional Analysis" in dashboard_selection:
                st.markdown("## Additional Analysis")
                if len(graph_data["FW"].unique())>2:
                        x = graph_data.groupby('FW').size()
                        df = pd.DataFrame(x, columns=['Count'])
                        df["FW"]  = df.index
                        fig = px.scatter(data_frame=df, x="FW", y="Count",title = "Overall Trend of SEMS",color_discrete_sequence = ['gold'])
                        fig.update_layout(xaxis=dict(showgrid=False),
                                          yaxis=dict(showgrid=False)
                                          )
                        fig.update_traces(mode='lines')
                        st.plotly_chart(fig, use_container_width=True)
                x = graph_data.groupby('SEM Issue Type').size()
                df = pd.DataFrame(x, columns=['Count'])
                df["SEM Issue Type"] = df.index
                df = df.sort_values('Count', ascending=[False])
                df = df.head(n=10)
                fig = px.histogram(data_frame=df, x="SEM Issue Type", y="Count", title="Top 10 Most Common Issues", text_auto=True,
                                   color_discrete_sequence=['gold'])
                fig.update_layout(xaxis=dict(showgrid=False),
                                  yaxis=dict(showgrid=False)
                                  )

                st.plotly_chart(fig, use_container_width=True)
                x = graph_data.groupby('Root Cause').size()
                df = pd.DataFrame(x, columns=['Count'])
                df["Root Cause"] = df.index
                df = df.sort_values('Count', ascending=[False])
                df = df.head(n=10)
                fig = px.histogram(data_frame=df, x="Root Cause", y="Count", title="Top 10 Root Cause",text_auto=True,
                                 color_discrete_sequence=['gold'])
                fig.update_layout(xaxis=dict(showgrid=False),
                                  yaxis=dict(showgrid=False)
                                  )

                st.plotly_chart(fig, use_container_width=True)

                # ----------------------------- Carrier Analysis -------------------------
                st.markdown("<hr/>", unsafe_allow_html=True)
            if "Carrier" in dashboard_selection:
                st.markdown("## Carrier Analysis")


                # Carriers by Total Sems
                x = graph_data.groupby('Carrier').size()
                df_total = pd.DataFrame(x, columns=['Count'])
                df_total["Carrier"] = df_total.index
                df_total = df_total.sort_values('Count', ascending=[False])
                df_total = df_total.head(n=10)
                fig = px.histogram(data_frame=df_total, x='Carrier', y="Count", title = "Top 10 Carriers by SEMS created",color_discrete_sequence=['gold'],
                                   text_auto=True)
                st.plotly_chart(fig, use_container_width=True)

                # Carrier by Open SEMS
                df_open = open_status_df(graph_data)
                x = df_open.groupby('Carrier').size()
                df_open = pd.DataFrame(x, columns=['Count'])
                df_open['Carrier'] = df_open.index
                df_open = df_open.sort_values('Count', ascending=[False])
                df_open = df_open.head(n=10)
                fig = px.histogram(data_frame=df_open, x='Carrier', y="Count",
                                   title="Top 10 Carriers by Open SEMS", color_discrete_sequence=['gold'],
                                   text_auto=True)
                st.plotly_chart(fig, use_container_width=True)
                def action_day_hist():
                    x = graph_data.groupby('Carrier')["Action Age [Days]"].mean()
                    df_open = pd.DataFrame(x, columns=["Action Age [Days]"])
                    df_open["Action Age [Days]"] = df_open["Action Age [Days]"].round(2)
                    df_open['Carrier'] = df_open.index
                    df_open = df_open.sort_values("Action Age [Days]", ascending=[False])
                    df_open = df_open.head(n=10)
                    fig = px.histogram(data_frame=df_open, x='Carrier', y="Action Age [Days]",
                                       title="Top 10 Carriers by Action Day Length", color_discrete_sequence=['gold'],
                                       text_auto=True)
                    st.plotly_chart(fig, use_container_width=True)
                action_day_hist()


                #-------------------------- Carrier DEEP DIVE ----------------------------
                st.markdown("<hr/>", unsafe_allow_html=True)
                st.markdown("## Top 5 Carrier Deep Dive")





                # TOP CARRIER
                def carrier(number,colour):
                    st.markdown("### " +str(number+1) + ". " + str(df_total['Carrier'].iloc[number]))
                    carrier = str(df_total['Carrier'].iloc[number])
                    carrier_df = graph_data[graph_data["Carrier"].str.contains(carrier, na=False)]

                    def issue_graph():
                        x = carrier_df.groupby('SEM Sub issue Type').size()
                        carrier_issue_df = pd.DataFrame(x, columns=['Count'])
                        carrier_issue_df["SEM Sub issue Type"] = carrier_issue_df.index
                        carrier_issue_df = carrier_issue_df.sort_values('Count', ascending=[False])
                        carrier_issue_df = carrier_issue_df.head(n=10)
                        fig = px.histogram(data_frame=carrier_issue_df, x='SEM Sub issue Type', y="Count", title="Top 10 SEM Sub-Issues for " + carrier,
                                           color_discrete_sequence=[colour],
                                           text_auto=True)
                        st.plotly_chart(fig, use_container_width=True)
                    def customer_affected_graph():
                        x = carrier_df.groupby('Sold-To ID').size()
                        carrier_cust_affected_df = pd.DataFrame(x, columns=['Count'])
                        carrier_cust_affected_df["Sold-To ID"] = carrier_cust_affected_df.index
                        carrier_cust_affected_df= carrier_cust_affected_df.sort_values('Count', ascending=[False])
                        carrier_cust_affected_df = carrier_cust_affected_df.head(n=10)
                        fig = px.histogram(data_frame=carrier_cust_affected_df, x='Sold-To ID', y="Count",
                                           title="Top 10 Customers affected by " + carrier,
                                           color_discrete_sequence=[colour],
                                           text_auto=True)
                        st.plotly_chart(fig, use_container_width=True)
                    issue_graph()
                    customer_affected_graph()
                    st.markdown("<hr/>", unsafe_allow_html=True)
                carrier(0,"#FFAC81")
                carrier(1,"#FF928B")
                carrier(2,"#FEC3A6")
                carrier(3,"#EFE9AE")
                carrier(4,"#CDEAC0")





