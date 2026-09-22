const $ = id => document.getElementById(id);

function fillList(id, items){
  const el = $(id);
  el.innerHTML = "";
  (items || []).forEach(item => {
    const li = document.createElement("li");
    li.textContent = item;
    el.appendChild(li);
  });
}

async function loadQt(){
  try{
    const res = await fetch(`./data/today.json?t=${Date.now()}`, {cache:"no-store"});
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    $("loading").classList.add("hidden");
    $("date").textContent = data.date ? `· ${data.date}` : "";

    if(data.status !== "ok"){
      $("unavailable").classList.remove("hidden");
      $("errorText").textContent = data.error || "공식 정보를 확인하지 못했습니다.";
      $("sourceLinkUnavailable").href = data.source_url;
      return;
    }

    $("content").classList.remove("hidden");
    $("title").textContent = data.title || "오늘의 QT";
    $("reference").textContent = data.bible_reference || "";
    $("summary").textContent = data.summary || "";
    fillList("meditation", data.meditation);
    fillList("application", data.application);
    $("prayer").textContent = data.prayer || "";
    $("notice").textContent = data.notice || "";
    $("sourceLink").href = data.source_url;
    $("generated").textContent = data.generated_at ? `생성: ${data.generated_at}` : "";
  }catch(err){
    $("loading").classList.add("hidden");
    $("unavailable").classList.remove("hidden");
    $("errorText").textContent = `데이터 로딩 오류: ${err.message}`;
    $("sourceLinkUnavailable").href = "https://www.duranno.com/qt/default.asp";
  }
}
loadQt();
