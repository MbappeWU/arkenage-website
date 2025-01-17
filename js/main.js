document.addEventListener('DOMContentLoaded', () => {
    // 平滑滚动
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // 导航栏滚动效果
    let header = document.querySelector('header');
    let lastScroll = 0;

    window.addEventListener('scroll', () => {
        const currentScroll = window.pageYOffset;

        if (currentScroll <= 0) {
            header.classList.remove('scroll-up');
            return;
        }

        if (currentScroll > lastScroll && !header.classList.contains('scroll-down')) {
            header.classList.remove('scroll-up');
            header.classList.add('scroll-down');
        } else if (currentScroll < lastScroll && header.classList.contains('scroll-down')) {
            header.classList.remove('scroll-down');
            header.classList.add('scroll-up');
        }
        lastScroll = currentScroll;
    });

    // 游戏加载处理
    const playButton = document.querySelector('.play-button');
    if (playButton) {
        playButton.addEventListener('click', (e) => {
            e.preventDefault();
            const gameContainer = document.querySelector('.game-container');
            // 使用全屏iframe加载游戏
            gameContainer.innerHTML = `
                <iframe 
                    src="https://arkenage.netlify.app" 
                    frameborder="0" 
                    style="width: 100%; height: 600px; border-radius: 10px;"
                    allowfullscreen
                ></iframe>
            `;
            // 移除游戏占位符
            const placeholder = document.querySelector('.game-placeholder');
            if (placeholder) {
                placeholder.style.display = 'none';
            }
        });
    }
}); 