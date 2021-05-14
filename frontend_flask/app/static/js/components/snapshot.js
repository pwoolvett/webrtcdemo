
let tmpl = document.createElement('template');
tmpl.innerHTML = `
<link rel="stylesheet"
href="https://fonts.googleapis.com/css?family=Roboto:regular,bold,italic,thin,light,bolditalic,black,medium&amp;lang=en">
<link rel="stylesheet" href="https://fonts.googleapis.com/icon?family=Material+Icons">
<link rel="stylesheet" href="https://code.getmdl.io/1.3.0/material.cyan-light_blue.min.css">

<style>
  .demo-card-wide.mdl-card {
    awidth: 360px;
    aheight: 300px;
  }
  .demo-card-wide > .mdl-card__title {
    color: #fff;
    aheight: 66%;
    {# background: url('../assets/demos/welcome_card.jpg') center / cover; #}
  }
  .demo-card-wide > .mdl-card__menu {
    color: #fff;
  }
  .demo-card-wide > .mdl-card__actions {
    display: flex;
    box-sizing:border-box;
    align-items: center;
  }
  </style>

  <div class="demo-card-wide mdl-card mdl-shadow--2dp">
    <div class="mdl-card__title", id="thumbnail" style="padding:0;">
      <video width="360" height="200" controls>
        <source id="video_url">
        Your browser does not support the video tag.
      </video> 

    </div>
    <div class="mdl-card__supporting-text">
      <b id="type">TYPE</b><br>
      <div style="display: inline-block;">
        <p id="start-date" style="display: inline-block;">START_DATE</p>
        ・
        <p id="location" style="display: inline-block;">asdg</p>
      </div>
    </div>

    <div class="mdl-card__actions mdl-card--border">
      <a
      class="mdl-button mdl-button--colored mdl-js-button mdl-js-ripple-effect"
      id="download-anchor"
      download
      >
        Download
      </a>
      <div class="mdl-layout-spacer"></div>
      <i class="material-icons">download</i>
    </div>

  </div>
`;


class VideoSnapshot extends HTMLElement {
  // consutrcots
  constructor() {
    // If you define a constructor, always call super() first!
    // This is specific to CE and required by the spec.
    super();
    // Attach a shadow root to the element.
    let shadowRoot = this.attachShadow({mode: 'open'});
    shadowRoot.appendChild(tmpl.content.cloneNode(true));
  }

  //   lifecycle
  connectedCallback() {
    // this.addEventListener("click", this.download);
  }
  disconnectedCallback() {
    // this.removeEventListener("click", this.download);
  }
  

  set thumbnail(image_url) {
    let thumbnailElement = this.shadowRoot.getElementById('thumbnail');
    let newVal = `url('${image_url}') center / cover`;
    thumbnailElement.style.background = newVal;
  }

  get url() {
    return this.shadowRoot.getElementById('video_url').src;
  }

  set url(video_url) {
    let sourceElement = this.shadowRoot.getElementById('video_url');
    let src = video_url;
    let ext = video_url.split(".").pop();
    let type = `video/${ext}`;

    sourceElement.src = src;
    sourceElement.type = type;

    this.shadowRoot.getElementById('download-anchor').href = video_url;

    
  }

  get eventType() {
    return this.shadowRoot.getElementById('type').innerHTML;
  }
  set eventType(eventType) {
    if (!eventType) {
      return 
    }
    let sourceElement = this.shadowRoot.getElementById('type');
    sourceElement.innerHTML = eventType;
  }

  get datetime() {
    return this.shadowRoot.getElementById('start-date').innerHTML;
  }
  set datetime(date_time) {
    if (!date_time) {
      return 
    }
    let sourceElement = this.shadowRoot.getElementById('start-date');
    sourceElement.innerHTML = date_time;
  }
  get location() {
    return this.shadowRoot.getElementById('location').innerHTML;
  }
  set location(location_) {
    if (!location_) {
      return 
    }
    let sourceElement = this.shadowRoot.getElementById('location');
    sourceElement.innerHTML = location_;
  }
  

  attributeChangedCallback(attrName, oldVal, newVal) {
    if (attrName == "thumbnail"){
        this.thumbnail = newVal;
        return;
      }
    if (attrName == "video-src"){
      this.url = newVal;
      return;
    }
    if (attrName == "event-type"){
      this.eventType = newVal;
      return;
    }
    if (attrName == "start-datetime"){
      this.datetime = newVal;
      return;
    }
    if (attrName == "location"){
      this.location = newVal;
      return;
    }

  }

  //
  static get observedAttributes() {
    return [
      "thumbnail",
      "video-src",
      "event-type",
      "start-datetime",
      "location",
  ];
  }

}
customElements.define("video-snapshot", VideoSnapshot);
