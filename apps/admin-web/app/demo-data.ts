export const metrics = {
  catalogServices: 6614,
  documents: 10,
  errors: 1,
  extractedItems: 8877,
  normalizationPercent: 99.95,
  reviewQueue: 4,
};

export const services = [
  {
    external_service_id: "svc-0001",
    name: "Консультация терапевта",
    partner: "Клиника 1",
    resident_price_kzt: 7000,
    nonresident_price_kzt: 9000,
    status: "опубликовано",
  },
  {
    external_service_id: "svc-0014",
    name: "МРТ головного мозга",
    partner: "Клиника 2",
    resident_price_kzt: 25000,
    nonresident_price_kzt: 32000,
    status: "опубликовано",
  },
  {
    external_service_id: "svc-0078",
    name: "УЗИ брюшной полости",
    partner: "Клиника 6",
    resident_price_kzt: 12000,
    nonresident_price_kzt: 15000,
    status: "проверено",
  },
];

export const partners = [
  { external_partner_id: "clinic-001", name: "Клиника 1", city: "Астана" },
  { external_partner_id: "clinic-002", name: "Клиника 2", city: "Алматы" },
  { external_partner_id: "clinic-006", name: "Клиника 6", city: "Караганда" },
];

export const unmatched = [
  {
    task_id: "RT-1042",
    partner: "Клиника 1",
    service_name_raw: "CHECK-UP",
    reason: "нет цены",
    priority: "Высокий",
  },
  {
    task_id: "RT-1043",
    partner: "Клиника 1",
    service_name_raw: "Диагностика инфекционных заболеваний",
    reason: "нет цены",
    priority: "Средний",
  },
  {
    task_id: "RT-1044",
    partner: "Клиника 1",
    service_name_raw: "Микробиологические исследования",
    reason: "нет цены",
    priority: "Средний",
  },
];
