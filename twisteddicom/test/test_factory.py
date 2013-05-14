from twisteddicom import pdu

def tf_A_ASSOCIATE_RQ():
    return pdu.A_ASSOCIATE_RQ(
        called_ae_title = "CALLED_AE_TITLE",
        calling_ae_title = "CALLING_AE_TITLE",
        application_context_item = test_factories[pdu.ApplicationContextItem](),
        presentation_context_items = [test_factories[pdu.A_ASSOCIATE_RQ.PresentationContextItem](i) for i in range(3)],
        user_information_item = test_factories[pdu.UserInformationItem]())

def tf_A_ASSOCIATE_AC():
    return pdu.A_ASSOCIATE_AC(
        application_context_item = test_factories[pdu.ApplicationContextItem](),
        presentation_context_items = [test_factories[pdu.A_ASSOCIATE_AC.PresentationContextItem](i) for i in range(3)],
        user_information_item = test_factories[pdu.UserInformationItem]())
    

def tf_ApplicationContextItem():
    return pdu.ApplicationContextItem(
        application_context_name = "ApplicationContextName")

def tf_A_ASSOCIATE_RQ_PresentationContextItem(presentation_context_id = 0):
    return pdu.A_ASSOCIATE_RQ.PresentationContextItem(
        presentation_context_id = presentation_context_id,
        abstract_syntax = test_factories[pdu.AbstractSyntaxSubitem](),
        transfer_syntaxes = [test_factories[pdu.TransferSyntaxSubitem](i) for i in range(3)])

def tf_A_ASSOCIATE_AC_PresentationContextItem(presentation_context_id = 0):
    return pdu.A_ASSOCIATE_AC.PresentationContextItem(
        presentation_context_id = presentation_context_id,
        result_reason = 0,
        transfer_syntax = test_factories[pdu.TransferSyntaxSubitem](1))


def tf_UserInformationItem():
    return pdu.UserInformationItem(user_data_subitems = [tf_DummyItem(i) for i in range(4711,4714)])

def tf_AbstractSyntaxSubitem():
    return pdu.AbstractSyntaxSubitem(abstract_syntax_name = "ABSTRACT_SYNTAX_NAME")

def tf_TransferSyntaxSubitem(i = 0):
    return pdu.TransferSyntaxSubitem(transfer_syntax_name = "TRANSFER_SYNTAX_NAME_%i" % (i,))

def tf_P_DATA_TF(data_values = ((0, "HEJ"),)):
    return pdu.P_DATA_TF(data_values)

def tf_DummyItem(dummy_id = 4711):
    return pdu.DummyItem(dummy_id = dummy_id)
    
def tf_A_ABORT(reason_diag = 0, source = 0):
    return pdu.A_ABORT(reason_diag = reason_diag, source = source)

    
    
    

test_factories = {
    pdu.A_ASSOCIATE_RQ: tf_A_ASSOCIATE_RQ,
    pdu.A_ASSOCIATE_AC: tf_A_ASSOCIATE_AC,
    pdu.ApplicationContextItem: tf_ApplicationContextItem,
    pdu.A_ASSOCIATE_RQ.PresentationContextItem: tf_A_ASSOCIATE_RQ_PresentationContextItem,
    pdu.A_ASSOCIATE_AC.PresentationContextItem: tf_A_ASSOCIATE_AC_PresentationContextItem,
    pdu.UserInformationItem: tf_UserInformationItem,
    pdu.AbstractSyntaxSubitem: tf_AbstractSyntaxSubitem,
    pdu.TransferSyntaxSubitem: tf_TransferSyntaxSubitem,
    pdu.P_DATA_TF: tf_P_DATA_TF,
    pdu.A_ABORT: tf_A_ABORT,
    
    pdu.DummyItem: tf_DummyItem,
}
