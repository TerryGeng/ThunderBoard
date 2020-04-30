var socket = io();
var client_id = null;
socket.on('connect', function () {
    socket.emit('join');
});
socket.on('new object available', function (obj_id) {
    socket.emit('subscribe', { obj_id: obj_id, client_id: client_id });
});
socket.on('id assigned', function (id) {
    console.log("Client id assigned " + id.toString());
    client_id = id;
});
socket.on('update', function (json) {
    updateObject(json);
});
socket.on('inactive', function (id) {
    if (id in $objects) {
        $objects[id].active = false;
        $objects[id].status.removeClass("text-success").removeClass("blinking").removeClass("mdi-play")
            .addClass("text-danger").addClass("mdi-stop");
        $objects[id].card.removeClass("objectActive");
    }
});
socket.on('close', function (id) {
    if (id in $objects) {
        $objects[id].card.find(".objectActionClose").click();
    }
});

var $objects = {};
var $objectTemplateDiv = $("#objectTemplate");
var $boards = {};
var $activeBoard = "";
var $columnLeftTemplate = $("#columnLeftTemplate");
var $columnRightTemplate = $("#columnRightTemplate");
var $boardDiv = $("#boardDiv");
var $unsubscribed = [];

var $boardNavItemTemplate = $("#boardNavItemTemplate");

function setActiveFlag(id, active=true){
    if(active){
        $objects[id].status.removeClass("text-danger").removeClass("mdi-stop");
        $objects[id].status.addClass("text-success").addClass("blinking").addClass("mdi-play");
        $objects[id].card.addClass("objectActive");
    } else {
        $objects[id].status.removeClass("text-success").removeClass("blinking").removeClass("mdi-play")
            .addClass("text-danger").addClass("mdi-stop");
        $objects[id].card.removeClass("objectActive");
    }
}

function getBoard(board){
    if (board in $boards){
        return $boards[board];
    } else {
        var nav = $boardNavItemTemplate.clone();
        $boards[board] = {
            left: $columnLeftTemplate.clone().attr('id', 'columnLeft_' + board).appendTo($boardDiv),
            right : $columnRightTemplate.clone().attr('id', 'columnRight_' + board).appendTo($boardDiv),
            unreadBadge: nav.find('.boardUnread'),
            unreadCount: 0,
            objects: []
        };
        nav.attr('id', 'boardNavItem_' + board);
        nav.appendTo($boardNavItemTemplate.parent());
        nav.find('.boardName').html(board);
        nav.find('.nav-link').on('click', function(){ toggleBoard(board); });
        nav.find('.boardClose').on('click', function (){ closeBoard(board) });
        nav.show();

        $('.boardNavDroppable').droppable({
            accept: ".objectCard",
            tolerance: "pointer",
            classes: {
                "ui-droppable-active": "alert-warning",
                "ui-droppable-hover": "alert-danger",
            },
            drop: function (event, ui){
                var moveTo = $(event.target).find('.boardName').html();
                moveCardToBoard(ui.draggable, moveTo);
            }
        });

        setSortable();
        return $boards[board];
    }
}

function closeBoard(board){
    $("#boardNavItem_" + board).fadeOut();
    $boards[board].left.remove();
    $boards[board].right.remove();
    for (let index in $boards[board].objects){
        socket.emit('unsubscribe', { obj_id: $boards[board].objects[index], client_id: client_id  });
        delete $objects[$boards[board].objects[index]];
    }
    delete $boards[board];
}

function moveCardToBoard(card, board){
    var id = card.attr("id").substring("object_".length);
    console.log("move " + id + " to " + board);
    var old_board = $boards[$objects[id].board];
    old_board.objects.splice(old_board.objects.indexOf(id));
    card.remove();

    $objects[id].json.board = board;
    initObject($objects[id].json, card.clone()); // according to jquery-ui's docs, object must be cloned.
    setSortable();
}

function toggleBoard(board){
    $activeBoard = board;
    $boardNavItemTemplate.parent().find('.nav-link').removeClass('active');
    $("#boardNavItem_" + board).find('.nav-link').addClass('active');
    for (let key in $boards){
        if (key === board) {
            $boards[key].left.show();
            $boards[key].right.show();
            $boards[key].unreadBadge.hide();
            $boards[key].unreadCount = 0;
        } else {
            $boards[key].left.hide();
            $boards[key].right.hide();
        }
    }
}

function initObject(json, existed_card=null){
    var card = null;
    if (existed_card) {
        card = existed_card;
    } else {
        card = $objectTemplateDiv.clone();
    }
    card.attr("id", "object_" + json.id);
    $objects[json.id] = {
        json: json,
        board: json.board,
        card: card,
        status: card.find(".objectStatusIcon"),
        title: card.find(".objectTitle"),
        content: card.find(".objectContent"),
        needInit: true,
        active: false
    };

    var board = getBoard(json.board);
    if (board.left.children().length === 0){
        card.appendTo(board.left);
    } else {
        card.insertBefore(board.left.children().first());
    }
    board.objects.push(json.id);
    var close_action = card.find(".objectActionClose");
    close_action.on('click', function (){
        $unsubscribed.push(json.id);
        socket.emit('unsubscribe', { obj_id: json.id, client_id: client_id });
        delete $objects[json.id];
    });

    card.attr("style", "");
}

function updateObject(json){
    if ($unsubscribed.indexOf(json.id) >= 0){
        return;
    }
    if (!(json.id in $objects)) {
        console.log("create new object " + json.id);
        initObject(json);
        toggleBoard(json.board);
    }

    $objects[json.id].json = json;
    $objects[json.id].title.html(json.name);

    if (!($objects[json.id].active === json.active)){
        $objects[json.id].active = json.active;
        setActiveFlag(json.id, json.active)
    }

    if (json.type === 'text'){
        if ($objects[json.id].needInit){ initTextObject(json); $objects[json.id].needInit = false; }
        updateTextObject(json);
    }else if (json.type === 'image'){
        if ($objects[json.id].needInit){ initImageObject(json); $objects[json.id].needInit = false; }
        updateImageObject(json);
    }else if (json.type === 'dialog'){
        if ($objects[json.id].needInit){ initDialogObject(json); $objects[json.id].needInit = false; }
        updateDialogObject(json);
    }

    if ($objects[json.id].board !== $activeBoard){
        $boards[$objects[json.id].board].unreadCount += 1;
        $boards[$objects[json.id].board].unreadBadge.html($boards[$objects[json.id].board].unreadCount).show();
    }

    $objects[json.id].card.show();
}

function initTextObject(json){
    $objects[json.id].content.css("max-height", "250px");
    $objects[json.id].content.css("overflow", "auto");
}

function updateTextObject(json){
    if(json.rotate === 'True') {
        if ($objects[json.id].content[0].scrollHeight - $objects[json.id].content.scrollTop() <= $objects[json.id].content.height()) {
            $objects[json.id].content.append("<span>" + json.data + "</span><br />");
            $objects[json.id].content.scrollTop($objects[json.id].content[0].scrollHeight);
        } else {
            $objects[json.id].content.append("<span>" + json.data + "</span><br />");
        }
    }else{
        $objects[json.id].content.html("<span>" + json.data + "</span>");
    }
}

function initImageObject(json){
    var img_id = "object_img_" + json.id;
    $objects[json.id].content.empty();
    var img = $(`<img id="${img_id}" src="data:image/jpeg;base64,${json.data}" />`);
    img.css("max-width", "100%");
    img.appendTo($objects[json.id].content);
    $objects[json.id].card.resizable({ handles: "n, s" });
    $objects[json.id].img = img;
    $objects[json.id].card.resize(function (){
        console.log($objects[json.id].content.height());
        $objects[json.id].img.height($objects[json.id].content.height());
    });
}

function updateImageObject(json){
    $objects[json.id].img.attr("src", `data:image/jpeg;base64,${json.data}`);
}

function setSortable() {
    // Make the dashboard widgets sortable Using jquery UI
    $('.connectedSortable').sortable({
        placeholder: 'sort-highlight',
        connectWith: '.connectedSortable',
        handle: '.card-header, .nav-tabs',
        forcePlaceholderSize: true,
        zIndex: 999999
    });
    $('.connectedSortable .card-header, .connectedSortable .nav-tabs-custom').css('cursor', 'move');
}

var $editSubscriptionModal = $("#editSubscriptionModal");
var $editSubscriptionCheckGroup = $("#editSubscriptionCheckGroup");
var $editSubscriptionCheckTemplate = $(".editSubscriptionCheckDiv");

$("#openEditSubscription").on("click", function(){
    socket.emit('list', {client_id: client_id});
    socket.on('list', function(obj_list){
        socket.off('list');
        editSubscriptionModalShow(obj_list);
    });
});

function editSubscriptionModalShow(obj_list){
    $editSubscriptionCheckGroup.empty();
    obj_list.forEach( function(_obj){
        var obj_check = $editSubscriptionCheckTemplate.clone();
        obj_check.find(".form-check-input").attr("id", "check_" + _obj.id).prop("checked", _obj.subscribed);
        obj_check.find(".form-check-label").html(_obj.board + " / " + _obj.name).attr("for", "check_" + _obj.id);
        obj_check.appendTo($editSubscriptionCheckGroup);
        obj_check.show();
    });

    $editSubscriptionModal.modal('show');
}

function editSubscriptionSubmit(){
    $editSubscriptionCheckGroup.find(".form-check-input").each(function (){
        var check = $(this);
        var id = check.attr("id").substring("check_".length);
        if (check.prop("checked")) {
            if (!(id in $objects)) {
                socket.emit('subscribe', {obj_id: id, client_id: client_id});
                if ($unsubscribed.indexOf(id) >= 0){
                    $unsubscribed.splice($unsubscribed.indexOf(id));
                }
            }
        } else {
            if (id in $objects){
                $objects[id].card.find(".objectActionClose").click();
            }
        }
    });
}

function cleanInactiveSubmit(){
    socket.emit('clean inactive');
}

// ------- Dialog -------

var dialogLabelTemplate = $(".dialogLabelTemplate");
var dialogInputTemplate = $(".dialogInputTemplate");
var dialogButtonTemplate = $(".dialogButtonTemplate");
var dialogSliderTemplate = $(".dialogSliderTemplate");

function initDialogObject(json){
    var dialog_id = "object_dialog_" + json.id;
    $objects[json.id].content.empty();
    $objects[json.id].groups = {};
    $objects[json.id].controls = {};


    for (item of json.fields){
        var temp_clone;

        if (item.type === "label"){
            temp_clone = dialogLabelTemplate.clone();
            var label = temp_clone.find(".dialogLabel");
            label.attr("id", dialog_id + "_" + item.name);
            label.html(item.text);
            $objects[json.id].controls[item.name] = {label: label};
        } else if (item.type === "input") {
            temp_clone = dialogInputTemplate.clone();
            var label = temp_clone.find(".dialogLabel");
            var input = temp_clone.find(".dialogInput");
            label.attr("id", dialog_id + "_" + item.name + "_label");
            label.html(item.text);
            input.attr("id", dialog_id + "_" + item.name + "_input");
            label.val(item.value);

            $objects[json.id].controls[item.name] = {label: label, input: input };
        } else if (item.type === "button") {
            temp_clone = dialogButtonTemplate.clone();
            var button = temp_clone.find(".dialogButton");
            button.attr("id", dialog_id + "_" + item.name);
            button.html(item.text);
            $objects[json.id].controls[item.name] = {button: button};
        }

        if (item.group in $objects[json.id].groups){
            temp_clone.children().appendTo($objects[json.id].groups[item.group]);
        } else {
            temp_clone.attr("id", dialog_id + "@" + item.group);
            $objects[json.id].groups[item.group] = temp_clone;
            temp_clone.appendTo($objects[json.id].content);
        }
    }
}

function updateDialogObject(json){
    for (item of json.fields){
        if (!(item.name in $objects[json.id].controls)){
            initDialogObject(json);
            return;
        }

        if (item.type === "label"){
            $objects[json.id].controls[item.name].label.html(item.text);
        } else if (item.type === "input") {
            $objects[json.id].controls[item.name].label.html(item.text);
            $objects[json.id].controls[item.name].input.val(item.value);
            $objects[json.id].controls[item.name].input.prop('disabled', !(item.enabled && json.active));
        } else if (item.type === "button") {
            $objects[json.id].controls[item.name].button.html(item.text);
            $objects[json.id].controls[item.name].button.prop('disabled', !(item.enabled && json.active));
        }
    }
}
