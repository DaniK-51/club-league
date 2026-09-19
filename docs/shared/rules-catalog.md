# 📜 Catalog of Rules & Criteria (v2)

Этот файл является **единственным источником правды** для реализации `RulesEngine`. Все значения баллов, лимитов и капов берутся отсюда.

## 🌐 Общие критерии (Common, C1–C11)
Доступны всем клубам независимо от направления.

| Code | Name (RU/EN) | Rule Type | Configuration (JSON Schema Example) | Limits / Caps |
|------|--------------|-----------|-------------------------------------|---------------|
| **C1** | Мероприятие клуба / Club organized an event | `tiered_with_bonus` | `{"tiers": [{"min":5,"max":15,"pts":400,"bonus_pts":200}, {"min":15,"max":50,"pts":600,"bonus_pts":300}, {"min":50,"max":100,"pts":800,"bonus_pts":400}, {"min":100,"max":null,"pts":1000,"bonus_pts":500}], "bonus_condition": {"field": "external_guests_percent", "operator": ">=", "value": 10}}` | Зрители не считаются. Регулярные тренировки не считаются. |
| **C2** | Совместное мероприятие / Joint event | `per_unit_with_bonus` | `{"base_per_partner": 300, "cross_type_bonus": 50}` | Мероприятие должно включать деятельность обоих клубов. |
| **C3** | Внутреннее кампусное мероприятие / Internal campus event | `binary` | `{"passive": 100, "active": 350}` | Пассивное: поделились оборудованием. Активное: стенд, подготовка. |
| **C4** | Пост в соцсетях / Social media post | `binary_with_monthly_cap` | `{"not_informative": 10, "informative": 50, "monthly_cap": 500}` | Публикация от аккаунта клуба. |
| **C5** | Эстетика соцсетей / Social media aesthetics | `fixed_monthly_with_per_unit` | `{"base_monthly": 200, "per_extra_social": 50}` | Мин. 2 поста/мес, шапка, хайлайты, двуязычность. |
| **C6** | Внешний спикер / External speaker | `scale` | `{"levels": {"local": 100, "regional": 200, "national": 400, "world": 500}}` | Не текущий студент/выпускник ИУ. Не более 2 раз/мес на одного спикера. |
| **C7** | Посещение внешнего мероприятия / Visited external event | `scale_with_frequency_limit` | `{"levels": {"city": 100, "kazan": 200, "other_rt": 300, "other_rf": 400, "abroad": 500}, "max_per_month": 1}` | Мин. 2-3 участника (зависит от направления). Клуб только посещает. |
| **C8** | Образовательный контент / Educational content | `tiered` | `{"tiers": [{"count": 1, "pts": 250}, {"min": 2, "max": 5, "pts": 500}, {"min": 6, "max": 10, "pts": 800}, {"min": 11, "max": null, "pts": 1000}]}` | Должен быть в открытом доступе. |
| **C9** | Упоминание в СМИ / Mentioned in media | `scale_with_conditional_bonus` | `{"levels": {"student": 100, "iu": 200, "city": 300, "region": 400, "federal": 500}, "full_club_focus_bonus": {"student": 150, "iu": 250, "city": 350, "region": 500, "federal": 600}, "max_full_focus_per_month": 5}` | Личный соц. аккаунт не считается. |
| **C10** | Помощь менеджеру / Assistance to manager | `discretionary` | `{"min": 50, "max": 300}` | На усмотрение администратора. |
| **C11** | Тимбилдинг / Team building | `fixed_per_event_with_monthly_cap` | `{"per_event": 350, "monthly_cap": 700}` | Нужен план + фотоотчет. Чаепитие без плана не считается. |

## ⚽ Специальные критерии: Спорт (Sport, S1–S4)
| Code | Name | Rule Type | Configuration | Limits / Caps |
|------|------|-----------|---------------|---------------|
| **S1** | Личные соревнования / Individual competition | `scale` | `{"levels": {"city": 100, "kazan": 200, "regional": 400, "rf": 1000, "world": 1400}}` | Мин. 2 представителя. Хост-клуб не получает баллы за участие в своем соревновании. |
| **S2** | Командные соревнования / Team competition | `scale_with_league_bonus` | `{"levels": {"internal_city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1500}, "league_bonus": {"internal_city": 0, "kazan": 50, "regional": 150, "rf": 250, "world": 500}}` | Однократное начисление за лигу + бонус. |
| **S3** | Победа в соревновании / Competition win | `scale_with_conditional_modifier` | `{"individual": {"city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1500}, "team": {"city": 300, "kazan": 500, "regional": 700, "rf": 1500, "world": 3000}, "host_win_modifier": {"condition": "invited_teams < host_teams", "factor": 0.5}}` | Если хост-клуб побеждает при малом числе приглашенных, баллы ×0.5 (или на усмотрение модератора). **Seed hybrid:** `reportData.host_underdog >= 1` + `host_win_factor=0.5` (формула invited/hosts — продуктовый rulebook). |
| **S4** | Регулярные тренировки / Regular training | `per_person_per_month` | `{"per_trainer_per_month": 100, "max_trainers": 3}` | |

## 💻 Специальные критерии: Технари (Tech, T1–T3)
| Code | Name | Rule Type | Configuration | Limits / Caps |
|------|------|-----------|---------------|---------------|
| **T1** | Хакатон/олимпиада (участие) / Hackathon participation | `scale` | `{"levels": {"internal_city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1500}}` | Мин. 2 участника. |
| **T2** | Хакатон/олимпиада (победа) / Hackathon win | `scale` | `{"levels": {"city": 300, "kazan": 500, "regional": 700, "rf": 1500, "world": 3000}}` | |
| **T3** | Выступление на конференции / Conference presentation | `binary_scale` | `{"local_meetup": 200, "large_conference": 400}` | Обязательно: логотип на слайдах, активная презентация. |

## 🎨 Специальные критерии: Арт (Art, A1–A4)
| Code | Name | Rule Type | Configuration | Limits / Caps |
|------|------|-----------|---------------|---------------|
| **A1** | Конкурс/фестиваль (участие) / Festival participation | `scale` | `{"levels": {"city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1400}}` | Мин. 2 представителя. |
| **A2** | Конкурс/фестиваль (победа) / Festival win | `scale_split_mode` | `{"individual": {"city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1500}, "team": {"city": 400, "kazan": 500, "regional": 700, "rf": 1500, "world_offline": 3000, "world_online": 2000}}` | |
| **A3** | Публичный перформанс / Public performance | `scale` | `{"levels": {"campus": 300, "city": 500, "regional": 800, "federal": 1200}}` | Открыто для зрителей. |
| **A4** | Художественный контент / Artistic content | `tiered` | `{"tiers": [{"count": 1, "pts": 200}, {"min": 2, "max": 5, "pts": 400}, {"min": 6, "max": 10, "pts": 700}, {"min": 11, "max": null, "pts": 1000}]}` | |

## 🎯 Специальные критерии: Special Interest (SI, I1–I4)
| Code | Name | Rule Type | Configuration | Limits / Caps |
|------|------|-----------|---------------|---------------|
| **I1** | Турнир по профилю (участие) / Profile tournament | `scale` | `{"levels": {"city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1400}}` | Мин. 2 представителя. |
| **I2** | Турнир по профилю (победа) / Profile tournament win | `scale_split_mode` | `{"individual": {"city": 200, "kazan": 400, "regional": 600, "rf": 1000, "world": 1500}, "team": {"city": 400, "kazan": 500, "regional": 700, "rf": 1500, "world_offline": 3000, "world_online": 2000}}` | |
| **I3** | Открытое публичное мероприятие / Open public event | `scale` | `{"levels": {"campus": 300, "city": 500, "regional": 800, "federal": 1200}}` | Открыто для не-членов клуба. |
| **I4** | Регулярные встречи / Regular meetings | `per_person_per_month` | `{"per_leader_per_month": 100, "max_leaders": 3}` | Формат регулярный и заранее объявленный. |

## 🌍 Глобальные правила (Global Rules)
Применяются после расчета индивидуальных баллов отчетов за месяц.

| Code | Name | Rule Type | Configuration |
|------|------|-----------|---------------|
| **G1** | Потолок соцсетей | `combined_cap` | `{"criteria_codes": ["C4", "C5"], "max_percent_of_total_monthly": 15}` |

---
**Примечание для ИИ/Разработчика:** При реализации `RulesEngine` каждый `rule_type` должен иметь соответствующий Pydantic-класс конфигурации и функцию-обработчик. Глобальные правила (G1) применяются к агрегированной сумме баллов клуба за месяц после обработки всех индивидуальных отчетов.
