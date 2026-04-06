// 通用JavaScript功能

// 自动刷新页面数据
function autoRefresh(interval = 30000) {
    setInterval(() => {
        if (document.visibilityState === 'visible') {
            window.location.reload();
        }
    }, interval);
}

// 格式化时间戳
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleString('zh-CN');
}

// 显示加载动画
function showLoading() {
    // 可以在需要时实现加载动画
}

// 隐藏加载动画
function hideLoading() {
    // 隐藏加载动画
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function () {
    console.log('游戏数据仪表板已加载');
});

// 初始化进度条宽度
document.querySelectorAll('.progress-bar[data-growth-stage]').forEach(bar => {
    const stage = parseInt(bar.getAttribute('data-growth-stage'));
    const width = stage <= 10 ? (stage / 10 * 100) : 100;
    bar.style.width = width + '%';
});