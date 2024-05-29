# _*_ coding :utf-8 _*_
# @Time : 2024/3/12 14:25
# @Author ：李文杰
from sqlalchemy import create_engine
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="数据概览",
    page_icon="📈",
)

# 数据库连接
DATABASE_URI = 'mysql+pymysql://root:198881@localhost/AnalysisDB'
engine = create_engine(DATABASE_URI)

st.title("📈 数据概览")

# 插入分割线
st.markdown("---")

# 统计摘要信息模块
st.header("数据源统计摘要信息")

def get_summary_stats(table_name):
    query = f"""
    SELECT 
        MIN(YEAR(PubDate)) AS StartYear, 
        MAX(YEAR(PubDate)) AS EndYear, 
        COUNT(*) AS Total
    FROM {table_name};
    """
    result = pd.read_sql_query(query, engine).iloc[0]
    return result

# 分别为每个表获取统计信息
weibo_stats = get_summary_stats("WeiboArticles")
toutiao_stats = get_summary_stats("ToutiaoArticles")
gov_stats = get_summary_stats("GovernmentArticles")

# 使用列布局展示统计摘要信息
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("微博帖子")
    st.write(f"时间范围：{weibo_stats['StartYear']} - {weibo_stats['EndYear']}")
    st.write(f"数据量：{weibo_stats['Total']}")

with col2:
    st.subheader("头条文章")
    st.write(f"时间范围：{toutiao_stats['StartYear']} - {toutiao_stats['EndYear']}")
    st.write(f"数据量：{toutiao_stats['Total']}")

with col3:
    st.subheader("政府文件")
    st.write(f"时间范围：{gov_stats['StartYear']} - {gov_stats['EndYear']}")
    st.write(f"数据量：{gov_stats['Total']}")

st.markdown("---")

# 展示年份占比饼图模块
st.header("各数据源年份文件数量占比")

#　展示年份占比
def get_yearly_distribution(table_name):
    query = f"""
    SELECT YEAR(PubDate) AS Year, COUNT(*) AS Total
    FROM {table_name}
    GROUP BY YEAR(PubDate)
    ORDER BY Year;
    """
    result = pd.read_sql_query(query, engine)
    return result

# 获取数据
weibo_distribution = get_yearly_distribution("WeiboArticles")
toutiao_distribution = get_yearly_distribution("ToutiaoArticles")
gov_distribution = get_yearly_distribution("GovernmentArticles")

# 创建饼图
fig_weibo = px.pie(weibo_distribution, values='Total', names='Year', title="微博帖子年份分布",
                   hover_data=['Total'], labels={'Total':'数量'})
fig_toutiao = px.pie(toutiao_distribution, values='Total', names='Year', title="头条文章年份分布",
                     hover_data=['Total'], labels={'Total':'数量'})
fig_gov = px.pie(gov_distribution, values='Total', names='Year', title="政府文件年份分布",
                 hover_data=['Total'], labels={'Total':'数量'})

# 更新图表布局来隐藏图例（如果需要）并优化悬浮提示信息
for fig in [fig_weibo, fig_toutiao, fig_gov]:
    fig.update_traces(textinfo='none', hoverinfo='label+percent', marker=dict(line=dict(color='#000000', width=2)))
    fig.update_layout(showlegend=True)

# Streamlit并排展示饼图
col1, col2, col3 = st.columns(3)
with col1:
    st.plotly_chart(fig_weibo, use_container_width=True)
with col2:
    st.plotly_chart(fig_toutiao, use_container_width=True)
with col3:
    st.plotly_chart(fig_gov, use_container_width=True)

st.markdown("---")

# 筛选器和数据展示模块
st.header("数据筛选和展示")

# 动态从数据库查询年份
# 动态从数据库查询年份
def get_years(source):
    table_map = {
        "政府文件": "GovernmentArticles",
        "头条文章": "ToutiaoArticles",
        "微博帖子": "WeiboArticles"
    }
    table = table_map.get(source, "GovernmentArticles")
    query = f"SELECT DISTINCT YEAR(PubDate) AS Year FROM {table} ORDER BY Year;"
    years = pd.read_sql_query(query, engine)['Year'].tolist()
    return years if years else [2022]


# 从WeiboArticles表查询省份

def get_provinces():
    query = """
    SELECT DISTINCT Province
    FROM WeiboArticles
    WHERE Province IS NOT NULL AND Province != ''
    ORDER BY Province;
    """
    provinces = pd.read_sql_query(query, engine)['Province'].tolist()
    return ['全部'] + provinces


data_sources = ['政府文件', '头条文章', '微博帖子']
col1, col2, col3 = st.columns(3)

with col1:
    selected_source = st.selectbox('选择数据源', data_sources, index=0, key='source_select')
    years = get_years(selected_source)

with col2:
    selected_year = st.selectbox('选择年份', years, index=0, key='year_select')

with col3:
    provinces = get_provinces()
    selected_province = st.selectbox('选择省份', provinces, index=0, key='province_select')


# 动态展示数据统计，默认显示前100条数据

def get_data_distribution(year, province, source):
    conditions = []
    if year != years[0]:  # 如果不是默认的第一个年份
        conditions.append(f"YEAR(PubDate) = {year}")
    if province != '全部':
        conditions.append(f"Province = '{province}'")

    where_clause = " AND ".join(conditions) if conditions else "1=1"  # 如果没有条件，则选择所有数据

    source_condition = {
        "政府文件": "GovernmentArticles",
        "头条文章": "ToutiaoArticles",
        "微博帖子": "WeiboArticles"
    }[source]

    query = f"SELECT * FROM {source_condition} WHERE {where_clause} LIMIT 100;"
    return pd.read_sql_query(query, engine)


distribution_df = get_data_distribution(selected_year, selected_province, selected_source)


# 使用expander控制详细的数据显示，让界面更加整洁
with st.expander("查看筛选结果"):
    if not distribution_df.empty:
        st.dataframe(distribution_df)
    else:
        st.write("没有找到匹配的数据。")
