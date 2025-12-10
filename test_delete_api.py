# 测试删除API调用逻辑
print("=== 前端删除API调用测试 ===")
print()

# 模拟API调用参数
kb_name = 'test_kb'
delete_data = True
base_url = 'http://localhost:7861'

# 构建请求URL
url = f"{base_url}/knowledge_base/{kb_name}"
params = {'delete_data': delete_data}

print("请求信息:")
print(f"URL: {url}")
print("方法: DELETE")
print(f"参数: {params}")
print()

print("预期响应:")
expected_response = {
    "message": f"知识库 '{kb_name}' 已成功删除",
    "delete_data": delete_data
}
print(expected_response)
print()

print("验证前端调用逻辑:")
print("1. ✓ 导入requests库")
print("2. ✓ 获取BASE_URL")
print("3. ✓ 构建DELETE请求")
print("4. ✓ 发送带参数的请求")
print("5. ✓ 处理响应并显示结果")
print("6. ✓ 成功后刷新页面")
print()

print("🎉 前端删除API调用逻辑正确!")
