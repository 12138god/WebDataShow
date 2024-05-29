from sqlalchemy import create_engine
import pandas as pd
import streamlit as st
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="文档探索",
    page_icon="📚",
)

# 数据库连接
DATABASE_URI = 'mysql+pymysql://root:G1988818god@rm-cn-bl03rfdi90002xho.rwlb.rds.aliyuncs.com/analysisdb'
engine = create_engine(DATABASE_URI)

st.title("📚文档探索")

def get_provinces():
    query = """
    SELECT DISTINCT Province
    FROM WeiboArticles
    WHERE Province IS NOT NULL AND Province != ''
    ORDER BY Province;
    """
    provinces = pd.read_sql_query(query, engine)['Province'].tolist()
    return ['全部'] + provinces

topics_dict = {
    '技术-基础': ['5G', '云计算', '大数据', '人工智能', '区块链', '物联网', '数字基建'],
    '应用-服务': ['电子商务', '工业互联网', '新零售', '在线教育', '直播经济', '智慧城市', '智慧服务', '智慧农业', '智慧物流', '智慧医疗', '智能制造'],
    '经济-发展': ['数字化转型', '平台经济', '数字贸易', '乡村振兴', '产业升级', '数字经济', '数字金融'],
    '治理-安全': ['生态保护', '数据安全', '数字司法', '数字政务', '数字治理', '网络安全'],
    '创新-人才': ['创新驱动', '科技创新', '教育创新', '人才培养', '创新投资', '技术创新']
}


# 使用columns让筛选器并列显示
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    # 数据来源选择，对应数据库表名转换
    source_mapping = {
        '头条': 'Toutiao',
        '微博': 'Weibo',
        '政府文件': 'Government'
    }
    data_source = st.selectbox('选择数据源', list(source_mapping.keys()), key='data_source')

with col2:
    # 年份选择
    year = st.selectbox('选择年份', [2020, 2021, 2022], key='year')

with col3:
    # 省份选择
    provinces = get_provinces()  # 假设这个函数已经定义
    province = st.selectbox('选择地区', provinces, key='province')

with col4:
    # 主题类别选择
    category = st.selectbox('选择主题类别', ['全部', '技术-基础', '应用-服务', '经济-发展', '治理-安全', '创新-人才'], key='category')

with col5:
    # 根据主题类别动态更新主题选项
    topics = ['全部'] + topics_dict.get(category, [])  # 假设topics_dict已经定义
    topic = st.selectbox('选择主题', topics, key='topic')

# 插入分割线以清晰区分筛选区域和结果展示区域
st.markdown("---")

# 根据筛选条件查询Topics表中的关键词和权重
def get_keywords(data_source, year, province, category):
    query = f"""
    SELECT Keyword1, Weight1, Keyword2, Weight2, Keyword3, Weight3,
           Keyword4, Weight4, Keyword5, Weight5, Keyword6, Weight6,
           Keyword7, Weight7, Keyword8, Weight8, Keyword9, Weight9,
           Keyword10, Weight10
    FROM Topics
    WHERE DataSource = '{data_source}'
    AND YEAR(PubDate) = {year}
    AND (Province = '{province}' OR '{province}' = '全部')
    AND (Category = '{category}' OR '{category}' = '全部');
    """
    return pd.read_sql_query(query, engine)

# 生成并展示词云图
def generate_wordcloud(keywords_df):
    keywords_dict = {}
    for index, row in keywords_df.iterrows():
        for i in range(1, 11):
            keyword = row[f'Keyword{i}']
            weight = row[f'Weight{i}']
            if keyword and weight:
                keywords_dict[keyword] = weight
    # st.dataframe(keywords_dict)
    # 指定微软雅黑字体路径以支持中文
    font_path = 'C:/Windows/Fonts/msyh.ttc'
    wordcloud = WordCloud(width=800, height=400, background_color='white', font_path=font_path).generate_from_frequencies(keywords_dict)

    # 创建一个图形对象
    fig, ax = plt.subplots()
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis("off")

    # 使用st.pyplot展示图形对象
    st.pyplot(fig)

keywords_df = get_keywords(source_mapping[data_source], year, province, category)
if not keywords_df.empty:
    generate_wordcloud(keywords_df)
else:
    st.write("没有找到匹配的关键词数据。")

st.markdown("---")
# 构造正确的表名
article_table = f"{source_mapping[data_source]}Articles"
association_table = f"{source_mapping[data_source]}ArticleTopicAssociation"

# 构造查询中的列名字符串
select_columns = "t.Label AS '主题标签', a.PubDate AS '发布日期', " + ("a.Title AS '标题', " if data_source != '微博' else "") +  ("a.Link AS '链接', " if data_source != '微博' else "") + "a.Content AS '全文'"

# 根据选择执行查询
query = f"""
SELECT
    {select_columns}
FROM
    Topics t
JOIN
    {association_table} ata ON t.TopicID = ata.TopicID
JOIN
    {article_table} a ON ata.ArticleID = a.ArticleID
WHERE
    YEAR(a.PubDate) = {year} AND
    (a.Province = '{province}' OR '{province}' = '全部') AND
    (t.Category = '{category}' OR '{category}' = '全部') AND
    (t.Label = '{topic}' OR '{topic}' = '全部')
LIMIT 100;
"""

try:
    results = pd.read_sql_query(query, engine)

    if not results.empty:
        with st.expander("查看筛选结果"):
            # 根据选择的数据源展示或隐藏标题列
            if data_source != '微博':
                columns_to_display = ['主题标签', '发布日期', '标题', '全文', '链接']
            else:
                columns_to_display = ['主题标签', '发布日期', '全文']  # 微博没有'标题', '链接'
            st.dataframe(results[columns_to_display])

        if data_source == '微博':
            format_func = lambda x: results.iloc[x]['全文'][:50] + '...' if len(results.iloc[x]['全文']) > 50 else results.iloc[x]['全文']
        else:
            format_func = lambda x: results.iloc[x].get('标题', '无标题')

        selected_index = st.selectbox('选择一篇文章来查看详细信息', range(len(results)), format_func=format_func, key='article_detail')
        if st.button('显示详细信息'):
            selected_article = results.iloc[selected_index]
            if data_source != '微博':
                details_md = f"""
- **主题标签:** {selected_article['主题标签']}
- **发布日期:** {selected_article['发布日期']}
- **标题:** {selected_article.get('标题', '无标题')}
- **全文:** {selected_article['全文']}
- **链接:** [阅读原文]({selected_article['链接']})
                """
            else:
                details_md = f"""
- **主题标签:** {selected_article['主题标签']}
- **发布日期:** {selected_article['发布日期']}
- **全文:** {selected_article['全文']}
                """
            st.markdown(details_md)
    else:
        st.write("没有找到匹配的文档。")
except Exception as e:
    st.error(f"查询时发生错误：{e}")
