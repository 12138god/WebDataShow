# _*_ coding :utf-8 _*_
# @Time : 2024/3/13 4:58
# @Author ：李文杰
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
import plotly.express as px
import folium
from folium.plugins import HeatMap
import streamlit.components.v1 as components
import plotly.graph_objects as go

# 数据库连接配置
DATABASE_URI = 'mysql+pymysql://root:198881@localhost/AnalysisDB'
engine = create_engine(DATABASE_URI)

# 页面布局
st.set_page_config(
    page_title="数据分析",
    page_icon="🔍",
)

@st.cache_data
def get_provinces():
    query = """
    SELECT DISTINCT Province
    FROM WeiboArticles
    WHERE Province IS NOT NULL AND Province != ''
    ORDER BY Province;
    """
    provinces = pd.read_sql_query(query, engine)['Province'].tolist()
    return ['全部'] + provinces

# 数据源对比
with st.container():
    st.title("数据源对比")
    # 从数据库查询数据
    @st.cache_data
    def get_data_source_comparison():
        query = """
        SELECT DataSource, Category, COUNT(*) AS ArticleCount
        FROM Topics
        JOIN GovernmentArticleTopicAssociation ON Topics.TopicID = GovernmentArticleTopicAssociation.TopicID
        GROUP BY DataSource, Category
        UNION ALL
        SELECT 'Toutiao' AS DataSource, Category, COUNT(*) AS ArticleCount
        FROM Topics
        JOIN ToutiaoArticleTopicAssociation ON Topics.TopicID = ToutiaoArticleTopicAssociation.TopicID
        GROUP BY DataSource, Category
        UNION ALL
        SELECT 'Weibo' AS DataSource, Category, COUNT(*) AS ArticleCount
        FROM Topics
        JOIN WeiboArticleTopicAssociation ON Topics.TopicID = WeiboArticleTopicAssociation.TopicID
        GROUP BY DataSource, Category;
        """
        return pd.read_sql_query(query, engine)


    df = get_data_source_comparison()

    # 获取唯一的数据源列表

    data_sources = df['DataSource'].unique()

    # 创建三列用于并排显示图表
    st.markdown("### 不同数据源主题关注度对比")
    col1, col2, col3 = st.columns(3)

    # 创建一个字典，将数据源与对应的Streamlit列关联起来

    columns = {data_sources[i]: col for i, col in enumerate([col1, col2, col3])}

    for source in data_sources:
        # 根据当前数据源筛选数据
        df_source = df[df['DataSource'] == source]

        # 转换数据为雷达图所需格式
        categories = df_source['Category'].tolist()
        values = df_source['ArticleCount'].tolist()

        # 雷达图需要闭环，因此在末尾添加第一个值来闭合图形
        categories += [categories[0]]
        values += [values[0]]

        # 创建雷达图

        fig_radar = go.Figure()

        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=source
        ))

        # 更新雷达图的布局
        fig_radar.update_layout(
            width=300,  # 设置宽度
            height=300,  # 设置高度
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(values)]  # 根据你的数据范围调整
                )),
            showlegend=False,
            title=f"{source} 主题关注度对比"
        )

        # 在对应的列中显示图表
        columns[source].plotly_chart(fig_radar, use_container_width=True)

    fig_heatmap = px.density_heatmap(df, x="DataSource", y="Category", z="ArticleCount", marginal_x="rug",
                                     marginal_y="histogram")
    st.markdown("### 数据源与主题类别间的文章分布热力图")
    st.plotly_chart(fig_heatmap, use_container_width=True)

    fig_parallel = px.parallel_categories(df, dimensions=['DataSource', 'Category', 'ArticleCount'],
                                          color="ArticleCount", color_continuous_scale=px.colors.sequential.Inferno)
    st.header("不同数据源中主题类别的文章数量平行坐标图")
    st.plotly_chart(fig_parallel, use_container_width=True)

st.markdown("---")


# 使用container容器组织主题趋势分析部分
@st.cache_data
def get_distinct_categories():
    query = "SELECT DISTINCT Category FROM Topics"
    with engine.connect() as conn:
        result = conn.execute(text(query))
        categories = [row['Category'] for row in result.mappings()]
    return categories


@st.cache_data
def get_distinct_labels(category=None):
    if category and category != '全部':
        query = "SELECT DISTINCT Label FROM Topics WHERE Category = :category"
        with engine.connect() as conn:
            result = conn.execute(text(query), {'category': category})
            labels = [row['Label'] for row in result.mappings()]
    else:
        query = "SELECT DISTINCT Label FROM Topics"
        with engine.connect() as conn:
            result = conn.execute(text(query))
            labels = [row['Label'] for row in result.mappings()]
    return labels


@st.cache_data
def get_document_count_by_period_and_source(category, label, data_sources):
    where_conditions = []
    if category != '全部':
        where_conditions.append(f"t.Category = '{category}'")
    if label != '全部':
        where_conditions.append(f"t.Label = '{label}'")

    union_queries = []
    for source in data_sources:
        table_name = f"{source}Articles"
        assoc_table_name = f"{source}ArticleTopicAssociation"
        union_query = f"""
        SELECT '{source}' AS Source, YEAR(a.PubDate) AS Year, 
               CASE WHEN MONTH(a.PubDate) <= 6 THEN 'H1' ELSE 'H2' END AS Half, 
               COUNT(*) AS DocumentCount
        FROM {table_name} a
        JOIN {assoc_table_name} ata ON a.ArticleID = ata.ArticleID
        JOIN Topics t ON ata.TopicID = t.TopicID
        """
        if where_conditions:
            union_query += "WHERE " + " AND ".join(where_conditions) + " \n"
        union_query += "GROUP BY Source, Year, Half"
        union_queries.append(union_query)

    if union_queries:
        query = "\nUNION ALL\n".join(union_queries)
        query += "\nORDER BY Year, Half, Source;"
        with engine.connect() as conn:
            df = pd.read_sql_query(text(query), conn)
        return df
    else:
        return pd.DataFrame()


with st.container():
    st.header("主题趋势分析")

    # 使用columns布局优化筛选器布局
    col1, col2, col3 = st.columns(3)
    with col1:
        categories = ['全部'] + get_distinct_categories()
        selected_category = st.selectbox("选择主题类别", categories)

    with col2:
        labels = ['全部'] + get_distinct_labels(selected_category)
        selected_label = st.selectbox("选择主题", labels)

    with col3:
        data_sources = st.multiselect("选择数据源", ["Government", "Toutiao", "Weibo"], default=[])

    if not data_sources:
        st.error("请选择至少一个数据源。")
    else:
        df = get_document_count_by_period_and_source(selected_category, selected_label, data_sources)

        if not df.empty:
            df['Period'] = df['Year'].astype(str) + " " + df['Half']
            # st.dataframe(df)
            fig = px.bar(df, x='Period', y='DocumentCount', color='Source', title='主题趋势（半年粒度）', barmode='stack')
            st.plotly_chart(fig)
        else:
            st.write("没有找到符合条件的数据")

st.markdown("---")
# 使用container容器组织地区主题偏好部分
# 使用@st.cache_data装饰器缓存获取省份信息的函数

@st.cache_data
def execute_query(query, params=None):
    with engine.connect() as conn:
        if params:
            return pd.read_sql_query(text(query), conn, params=params)
        else:
            return pd.read_sql_query(text(query), conn)

@st.cache_data
def get_categories():
    query = "SELECT DISTINCT Category FROM Topics"
    return ['全部'] + pd.read_sql(query, engine)['Category'].tolist()

def get_labels(category=None):
    if category and category != '全部':
        query = "SELECT DISTINCT Label FROM Topics WHERE Category = :category"
        with engine.connect() as conn:
            result = conn.execute(text(query), {'category': category})
            labels = [row['Label'] for row in result.mappings()]
    else:
        query = "SELECT DISTINCT Label FROM Topics"
        with engine.connect() as conn:
            result = conn.execute(text(query))
            labels = [row['Label'] for row in result.mappings()]
    return labels
@st.cache_data
def get_province_preference_data(data_sources, selected_years, selected_category, selected_label):
    query_params = {
        "start_year": selected_years[0],
        "end_year": selected_years[1],
        "category": selected_category,
        "label": selected_label
    }

    queries = []
    for source in data_sources:
        table_name = f"{source}Articles"
        assoc_table_name = f"{source}ArticleTopicAssociation"
        sub_query = f"""
        SELECT a.Province, COUNT(*) AS DocumentCount
        FROM {table_name} AS a
        JOIN {assoc_table_name} AS ata ON a.ArticleID = ata.ArticleID
        JOIN Topics AS t ON ata.TopicID = t.TopicID
        WHERE YEAR(a.PubDate) BETWEEN :start_year AND :end_year
        """
        if selected_category != '全部':
            sub_query += " AND t.Category = :category"
        if selected_label != '全部':
            sub_query += " AND t.Label = :label"
        sub_query += " GROUP BY a.Province"
        queries.append(sub_query)

    combined_query = " UNION ALL ".join(queries)
    return execute_query(combined_query, query_params)


# 使用container容器组织地区主题偏好分析部分
with st.container():
    st.header("地区主题偏好")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        categories = get_categories()
        selected_category = st.selectbox("选择主题类别", categories, key="category_preference")

    with col2:
        labels = get_labels(selected_category)
        selected_label = st.selectbox("选择主题", labels, key="label_preference")

    with col3:
        data_sources = st.multiselect("选择数据源", ["Government", "Toutiao", "Weibo"], default=[],
                                      key="data_source_preference")

    with col4:
        selected_years = st.slider("选择年份范围", 2019, 2023, (2019, 2023), key="year_range_preference")

    if data_sources and selected_years and (selected_category != '全部' or selected_label != '全部'):
        df_province_preference = get_province_preference_data(data_sources, selected_years, selected_category,
                                                       selected_label)
        # st.dataframe(df_province_preference)
        with st.container():
            col1, col2 = st.columns([3, 1])  # 分割屏幕空间，热力图占3/4，饼图及筛选器占1/4
            with col1:
                df_location = pd.read_csv('locations.csv')

                # 将省份名称转换为你的数据中相对应的名称
                df_location.rename(columns={'省份': 'Province', '经度': 'Longitude', '维度': 'Latitude'}, inplace=True)

                # 合并偏好数据和地理位置信息
                df_merged = pd.merge(df_province_preference, df_location, on='Province')

                # 创建地图，中心设置为中国，缩放级别调整以覆盖整个中国
                m = folium.Map(location=[35, 105], zoom_start=3.3)

                # 添加热力图层，调整参数以优化外观
                HeatMap(data=df_merged[['Latitude', 'Longitude', 'DocumentCount']], radius=20).add_to(m)

                # 使用CircleMarker代替Marker，可以通过调整radius来改变大小
                for i, row in df_merged.iterrows():
                    folium.CircleMarker(
                        location=[row['Latitude'], row['Longitude']],
                        radius=2,  # 控制圆点大小
                        popup=f"{row['Province']}: {row['DocumentCount']} documents",
                        fill=True,
                        color='blue',
                        fillColor='blue',
                        fillOpacity=0.6
                    ).add_to(m)

                # 在Streamlit中显示地图
                map_html = m._repr_html_()
                components.html(map_html, height=400, width=500)

            # 省份主题偏好
            with col2:
                # 下拉列表筛选器
                provinces = get_provinces()
                # 省份选择下拉筛选器
                selected_province = st.selectbox('选择地区', provinces, index=0, key='province_select')

                # 根据选择的省份进行联表查询
                if selected_province == '全部':
                    query = """
                        SELECT Category, COUNT(*) AS Count
                        FROM Topics
                        GROUP BY Category
                        """
                else:
                    query = f"""
                        SELECT Category, COUNT(*) AS Count
                        FROM Topics
                        WHERE Province = '{selected_province}'
                        GROUP BY Category
                        """

                df = pd.read_sql_query(query, engine)
                # st.dataframe(df)
                # 创建饼图
                fig_pie = px.pie(df, values='Count', names='Category', title='省份主题偏好')
                fig_pie.update_traces(textinfo='none', hoverinfo='label+percent',
                                      marker=dict(line=dict(color='#000000', width=2)))
                fig_pie.update_layout(height=300, showlegend=True)

                # 展示饼图
                st.plotly_chart(fig_pie, use_container_width=True)  # 使用容器宽度
    else:
        st.error("请确保选择了数据源并且至少选择了一个主题类别或主题。")

