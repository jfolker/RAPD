<?php

//prevents caching
header("Expires: Sat, 01 Jan 2000 00:00:00 GMT");
header("Last-Modified: ".gmdate("D, d M Y H:i:s")." GMT");
header("Cache-Control: post-check=0, pre-check=0",false);
session_cache_limiter();
session_start();

require('../config.php');
require('../functions.php');

//check for administrative rights
if (allow_access(Administrators) != "yes")
{
	include ('../no_access.html');
	exit;
}

?>

<head>
  <meta http-equiv="Content-Language" content="en-us">

  <style type="text/css" media="screen">
    @import url("../../css/rapd.css");
  </style>
</head>

<body class='banner' topmargin="0" leftmargin="0" rightmargin="0" bottommargin="0">
  <h1>RAPD Trips Administration</h1>
  <table border="0" width="100%" id="table1">
    <tr>
      <td align="center">
        <table border="0" width="800" id="table2" cellspacing="0" cellpadding="0">
	  <tr>
	    <td width="280">&nbsp;</td>
	  </tr>
	  <tr>
	    <td width="280"><b><font size="2">Rapd Trips Control Panel</font></b></td>
	  </tr>
	  <tr>
	    <td width="280">Logged in as <?php echo $_SESSION[username]; ?></td>
	  </tr>
          <tr>
            <td><a href="../../main.php">Main Page</a></td>
          </tr>
          <tr>
            <td><a href="adminpage.php">Administrative Control Panel</a></td>
          </tr>
	  <tr>
	    <td width="280"><a href="../logout.php">Logout</a></td>
	  </tr>
          <tr>
            <td width="280">
              <form action="<? $PHP_SELF; ?>" method="POST">
                <input type="hidden" name="clear" value="clear">
                <input type="submit" value="Clear Suggested Dirs" name="submit">
              </form>
            </td>
          </tr>
	  <tr>
            <td>
	      <form name="myform" id="myform" action="<? $PHP_SELF; ?>" method="POST">
                <table border="0" width="100%" id="table3" cellspacing="0" cellpadding="0" bordercolorlight="#C0C0C0" bordercolordark="#FFFFFF">
                  <tr>
                    <td width="140">Username:</td>
                    <td>
                      <select size="1" name="username1" onChange="document.myform.submit()">
<?php
//Clear suggested directories if asked to
if ($_POST[clear] == "clear")
  {
    clear_candidate_dirs();
  }

if ($_POST[username1] != "")
  {
    echo "<option>$_POST[username1]</option>";
    echo "<option value=\"\"></option>";
  }
elseif ($_SESSION[username1] != "")
  {
    echo "<option>$_SESSION[username1]</option>";
    echo "<option value=\"\"></option>";
  }  
else
  {
    echo "<option></option>";
  }

//require the config file
require ("../config.php");

//make the connection to the database
$connection = @mysql_connect($server, $dbusername, $dbpassword) or die(mysql_error());
$db = @mysql_select_db($db_name,$connection)or die(mysql_error());

//build and issue the query
$sql ="SELECT username FROM $table_name ORDER BY username";
$result = @mysql_query($sql,$connection) or die(mysql_error());
while ($sql = mysql_fetch_object($result))
  {
    $uname = $sql -> username;
    echo "<option value=\"$uname\">$uname</option>";
  }
?>
                      </select>
                    </td>
                  </table>
                </form>
              </tr> 
            </td>
          </tr>
          <tr>
            <td>
              <table border="0" width="100%" id="table4" cellspacing="0" cellpadding="2">
                <tr>
                  <td>      
<?php
  if (($_POST[username1] != "") || ($_SESSION[username1] != ""))
  {
    echo "<caption>Trips for $_POST[username1] </caption>";

    if ($_POST[username1] == "")
      {
	$_POST[username1] = $_SESSION[username1];
      }

    $_SESSION['username1'] =  $_POST[username1];   
    
    //require the config file
    require ("../config.php");

    //make the connection to the database
    $connection = @mysql_connect($server, $dbusername, $dbpassword) or die(mysql_error());
    $db = @mysql_select_db($db_name,$connection)or die(mysql_error());

    //build and issue the query
    $sql ="SELECT * FROM trips WHERE username = '$_POST[username1]' ORDER BY trip_start DESC";
    $result = @mysql_query($sql,$connection) or die(mysql_error());
    $i = mysql_num_rows($result);
    if ($i > 0)
      {
        echo "<tr><td class='header'>Start Date</td><td class='header'>Finish Date</td><td class='header'>Root Data Dir</td><td class='header'>Beamline</td></tr>";
	$j = 1;
        while ($sql = mysql_fetch_object($result))
	  {
	    $start    = $sql -> trip_start;
	    $finish   = $sql -> trip_finish;
	    $data     = $sql -> data_root_dir;
	    $beamline = $sql -> beamline;
	    
	    echo "<FORM METHOD=\"POST\" ACTION=\"removetrip.php\">";
	    if (fmod($j,2) == 0)
              {
                echo "  <tr bgcolor=\"EEEEFF\">";
              }
            else
              {
                echo "  <tr>";
	      }
            echo "    <td><input type=\"hidden\" name=\"start\" value=\"$start\">$start</td>";
	    echo "    <td><input type=\"hidden\" name=\"finish\" value=\"$finish\">$finish</td>";
	    echo "    <td><input type=\"hidden\" name=\"data\" value=\"$data\">$data</td>";
	    echo "    <td><input type=\"hidden\" name=\"beamline\" value=\"$beamline\">$beamline</td>";
	    echo "    <td><input type=\"submit\" value=\"Delete Trip\" name=\"submit\"></td>";
	    echo "  </tr>";
            echo "</FORM>";
            $j++;
	  }
      }
    else
      {
?>
	<tr>
        <td>No trips in database</td>
	</tr>
        <tr><td class='header'>Start Date</td><td class='header'>Finish Date</td><td class='header'>Root Data Dir</td><td class='header'>Beamline</td></tr>
        <tr>
          <td>
            Here's an example
          </td>
        </tr>
        <tr>
          <td>2009-08-19 11:03:00</td>
          <td>2009-08-19 23:54:00</td>
          <td>/gpfs3/users/cornell/Crane_Aug09</td>
          <td>C</td>
        </tr>
            
<?php
      } //END if ($i > 0)
?>
                 <FORM METHOD="POST" ACTION="addtrip.php">
                 <tr>
                   <td>&nbsp</td>
                   <td>&nbsp</td>
                   <td>
                      <select size="1" name="data1">
                        <option value=""></option>
                  
<?php

//make the connection to the database
$connection = @mysql_connect($server, $dbusername, $dbpassword) or die(mysql_error());
$db = @mysql_select_db($db_name,$connection)or die(mysql_error());

//build and issue the query
$sql2 = "SELECT * FROM candidate_dirs ORDER BY dir_id DESC";
$result2 = @mysql_query($sql2,$connection) or die(mysql_error());
while ($return2 = mysql_fetch_object($result2))
  {
    $dirname = $return2 -> dirname;
    echo "<option value=\"$dirname\">$dirname</option>";
  }
?>
                      </select>
                    </td>
                    <td>
                     <input type="text" name="beamline1" size="3">
                    </td>
                    <td>
                      <input type="submit" value="Add Trip" name="submit">
                    </td>
                 </tr>
                 <tr>
                   <td>&nbsp</td>
                   <td>&nbsp</td>
                    <td>
                      <input type="text" name="data" size="24">
                   </td>
                   <td>
                     <input type="text" name="beamline" size="3">
                   </td> 
                   <td>
                      <input type="submit" value="Add Trip" name="submit">
                 </form>
<?php
  } //END if ($_POST[username1] != "")
?>         
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
</body>
