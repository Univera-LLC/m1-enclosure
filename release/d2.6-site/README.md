# Mac mini M1 · Корпус FDM D2.6

[Задня панель у 3D](https://dvaderfun.github.io/mac-mini-m1-case-prototype/?view=rear) · [Т-кишеня зі звороту](https://dvaderfun.github.io/mac-mini-m1-case-prototype/?view=rear&part=panel&solo=1&side=back) · [Порівняння D2.5 і D2.6](d25-vs-d26-usb-audio-comparison.svg) · [Розріз Thunderbolt](d26-connector-section.svg).

За фото плати й першого помаранчевого друку D2.5 обидва USB-A та прямокутний вузол аудіо отримали спільну внутрішню кишеню. Лицьова площина змістилась назовні на 0,60 мм; загальна товщина панелі — 2,60 мм. Стінки перед пазами мають 0,80 мм біля USB-A, HDMI, RJ-45 та аудіо, 0,90 мм біля обох TB і 0,40 мм біля окремого PD IN. Буртик аудіо утоплений на 0,32 мм у CAD. Посадку з реальною платою та кабелями ще не перевірено. Насамперед звірте спільний екран двох TB: [перетин STL з референсом за фото — 0 мм³, з оригінальним SOURCE_20 — 37,49 мм³ саме в цій зоні](downloads/d2.6/reference-crosscheck.json).

[Малий комплект STL для першої примірки](downloads/d2.6/d2.6-first-fit.zip) · [інструкція](downloads/d2.6/FIT-FIRST.md) · [задня панель 02](downloads/d2.6/print/02-flat-rear-panel.stl) · [корпус: п’ять STL](downloads/d2.6/d2.6-cold-fit-kit.zip). Друкуйте 01–04 та зразки 06–08 з однієї ревізії; з D2.5 можна використати заглушку 05. Панель 02 орієнтовано лицем на стіл: PETG, 0,10 мм включно з першим шаром, без підтримок. Для першої примірки живлення не підключають.

[STEP п’яти друкованих деталей](downloads/d2.6/d26-printable.step) · [STEP збірки](downloads/d2.6/d26-assembly.step) · [редагований SolidCraft](downloads/d2.6/d26-workbench.sc) · [3D-референс плати Mac](reference/d2.6/mac-board-reference.glb) · [усі завантаження](https://dvaderfun.github.io/mac-mini-m1-case-prototype/#downloads). Одиниці друку й CAD — мм. Плата Mac і радіатор є сітками в GLB/SC; у STEP їх немає.

[Схема складання](d26-rear-assembly.jpg) · [розрахунок посадки портів](downloads/d2.6/ports-fit.json) · [нарізка PrusaSlicer](downloads/d2.6/print/slice-checks.json) · [три зняті антени та динамік](accessories/) · [джерела та ліцензії](ATTRIBUTION.md).

Попередні конструкції: [D2.5](d2.5/?view=rear) · [D2.4](d2.4/?view=rear) · [D2.3](d2.3/?view=rear) · [D2.2](d2.2/?view=rear) · [D2.1](d2.1/?view=rear) · [D2](d2/?view=rear) · [D1](d1/) · [H1](h1/?mode=hybrid).
