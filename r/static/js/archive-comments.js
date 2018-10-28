$(document).ready(function() {
  $('a.score').click(function(){
    var $comment = $(this).closest('.comment');
    var depth = parseInt($comment.data('depth'));
    if ($comment.hasClass('collapsed')) {
      $comment.removeClass('collapsed');
      $check_comment = $comment.next('.comment');
      depth_sibling = false;
      while (!depth_sibling) {
        if ($check_comment.length == 0) {
          depth_sibling = true;
        }
        if ($check_comment.data('depth') == '' || parseInt($check_comment.data('depth')) <= depth) {
          depth_sibling = true;
        } else {
          $check_comment.removeClass('hidden');
        }
        $check_comment = $check_comment.next('.comment');
      }
    } else {
      $comment.addClass('collapsed');
      $check_comment = $comment.next('.comment');
      depth_sibling = false;
      while (!depth_sibling) {
        if ($check_comment.length == 0) {
          depth_sibling = true;
        }
        if ($check_comment.data('depth') == '' || parseInt($check_comment.data('depth')) <= depth) {
          depth_sibling = true;
        } else {
          $check_comment.addClass('hidden');
        }
        $check_comment = $check_comment.next('.comment');
      }
    }
  });
});