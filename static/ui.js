console.log("loaded js");

$(document).ready(function() {
	$(".submit_button").click(function() {
        $.ajax({
            url:"/hash/",
            type:'post',
            data: $("#new_hash").val(),
            success:function(data){
            	obj = JSON.parse(data);
                if (obj != "Hash already exists") {
                    $('.hashes').append(
    	                "<div class='hash_row'>" + 
                        "<div class='hash_id'>ID: " + obj[0] + "</div>" + 
    	                "<div class='hash_string'>Hash:    " + obj[1] + "</div>" +
    	                "<div class='hash_start'>Created: " + obj[2] + "</div>" +
    	           		"</div>"
                    );
                }
            }
        });
	})
})